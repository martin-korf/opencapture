# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import uuid
import json

import pandas as pd
import zeep
import base64
import secrets
import logging
import datetime
import requests
from flask_babel import gettext
from zeep import Client, exceptions
from src.backend import verifier_exports
from src.backend.import_classes import _Files
from src.backend.import_models import verifier, accounts
from src.backend.import_controllers import auth, user, monitoring
from src.backend.main import launch, create_classes_from_custom_id
from flask import current_app, Response, request, g as current_context
from src.backend.functions import retrieve_custom_from_url, delete_documents


def handle_uploaded_file(files, workflow_id):
    custom_id = retrieve_custom_from_url(request)
    path = current_app.config['UPLOAD_FOLDER']
    tokens = []

    for file in files:
        _f = files[file]
        filename = _Files.save_uploaded_file(_f, path)

        now = datetime.datetime.now()
        year, month, day = [str('%02d' % now.year), str('%02d' % now.month), str('%02d' % now.day)]
        hour, minute, second, microsecond = [str('%02d' % now.hour), str('%02d' % now.minute), str('%02d' % now.second), str('%02d' % now.microsecond)]
        date_batch = year + month + day + '_' + hour + minute + second + microsecond
        token = date_batch + '_' + secrets.token_hex(32) + '_' + str(uuid.uuid4())
        tokens.append({'filename': os.path.basename(filename), 'token': token})

        task_id_monitor = monitoring.create_process({
            'status': 'wait',
            'module': 'verifier',
            'source': 'interface',
            'filename': os.path.basename(filename),
            'token': token,
            'workflow_id': workflow_id if workflow_id else None,
        })

        if task_id_monitor:
            launch({
                'file': filename,
                'custom_id': custom_id,
                'workflow_id': workflow_id,
                'task_id_monitor': task_id_monitor[0]['process'],
            })
        else:
            return False, 500
    return tokens, 200


def get_document_by_id(document_id):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        return document_info, 200
    else:
        response = {
            "errors": gettext('GET_DOCUMENT_BY_ID_ERROR'),
            "message": gettext(error)
        }
        return response, 400


def get_document_id_and_status_by_token(token):
    decoded_token, status = auth.decode_unique_url_token(token)
    if status == 500:
        return decoded_token, status

    process, _ = monitoring.get_process_by_token(decoded_token['sub'])

    if process['process'] and process['process'][0]:
        return process['process'][0], 200
    else:
        response = {
            "errors": gettext('GET_DOCUMENT_ID_AND_STATUS_BY_TOKEN_ERROR'),
            "message": gettext('GET_DOCUMENT_ID_AND_STATUS_BY_TOKEN_ERROR_MESSAGE')
        }
        return response, 400


def retrieve_documents(args):
    if 'where' not in args:
        args['where'] = []
    if 'data' not in args:
        args['data'] = []
    if 'select' not in args:
        args['select'] = []

    args['table'] = ['documents', 'form_models']
    args['left_join'] = ['documents.form_id = form_models.id']
    args['group_by'] = ['documents.id', 'documents.form_id', 'form_models.id']

    args['select'].append("DISTINCT(documents.id) as document_id")
    args['select'].append("to_char(register_date, 'DD-MM-YYYY " + gettext('AT') + " HH24:MI:SS') as date")
    args['select'].append('form_models.label as form_label')
    args['select'].append("*")

    if 'time' in args:
        if args['time'] in ['today', 'yesterday']:
            args['where'].append(
                "to_char(register_date, 'YYYY-MM-DD') = to_char(TIMESTAMP '" + args['time'] + "', 'YYYY-MM-DD')")
        else:
            args['where'].append("to_char(register_date, 'YYYY-MM-DD') < to_char(TIMESTAMP 'yesterday', 'YYYY-MM-DD')")

    if 'status' in args:
        args['where'].append('documents.status = %s')
        args['data'].append(args['status'])

    if 'form_id' in args and args['form_id']:
        if args['form_id'] == 'no_form':
            args['where'].append('documents.form_id is NULL')
        else:
            args['where'].append('documents.form_id = %s')
            args['data'].append(args['form_id'])

    if 'search' in args and args['search']:
        args['table'].append('accounts_supplier')
        args['left_join'].append('documents.supplier_id = accounts_supplier.id')
        args['group_by'].append('accounts_supplier.id')
        args['where'].append(
            "(LOWER(original_filename) LIKE '%%" + args['search'].lower() +
            "%%' OR LOWER((datas -> 'invoice_number')::text) LIKE '%%" + args['search'].lower() +
            "%%' OR LOWER(accounts_supplier.name) LIKE '%%" + args['search'].lower() + "%%')"
        )
        args['offset'] = ''
        args['limit'] = ''

    if 'allowedCustomers' in args and args['allowedCustomers']:
        args['where'].append('customer_id IN (' + ','.join(map(str, args['allowedCustomers'])) + ')')

    if 'allowedSuppliers' in args and args['allowedSuppliers']:
        if not args['allowedSuppliers'][0]:
            args['where'].append('supplier_id is NULL')
        else:
            args['where'].append('supplier_id IN (' + ','.join(map(str, args['allowedSuppliers'])) + ')')

    if 'purchaseOrSale' in args and args['purchaseOrSale']:
        args['where'].append('purchase_or_sale = %s')
        args['data'].append(args['purchaseOrSale'])

    total_documents = verifier.get_total_documents({
        'select': ['count(documents.id) as total'],
        'where': args['where'],
        'data': args['data'],
        'table': args['table'],
        'left_join': args['left_join'],
    })
    if total_documents not in [0, []]:
        documents_list = verifier.get_documents(args)
        for document in documents_list:
            year = document['register_date'].strftime('%Y')
            month = document['register_date'].strftime('%m')
            year_and_month = year + '/' + month
            thumb = get_file_content('full', document['full_jpg_filename'], 'image/jpeg',
                                     compress=True, year_and_month=year_and_month)
            document['thumb'] = str(base64.b64encode(thumb.get_data()).decode('UTF-8'))
            if document['supplier_id']:
                supplier_info, error = accounts.get_supplier_by_id({'supplier_id': document['supplier_id']})
                if not error:
                    document['supplier_name'] = supplier_info['name']
        response = {
            "total": total_documents[0]['total'],
            "documents": documents_list
        }
        return response, 200
    return '', 200


def update_position_by_document_id(document_id, args):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        column = position = ''
        for _position in args:
            column = _position
            position = args[_position]

        document_positions = document_info['positions']
        document_positions.update({
            column: position
        })
        _, error = verifier.update_document({
            'set': {"positions": json.dumps(document_positions)},
            'document_id': document_id
        })
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_POSITIONS_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def update_page_by_document_id(document_id, args):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        column = page = ''
        for _page in args:
            column = _page
            page = args[_page]

        document_pages = document_info['pages']
        document_pages.update({
            column: page
        })
        _, error = verifier.update_document({'set': {"pages": json.dumps(document_pages)}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_PAGES_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def update_document_data_by_document_id(document_id, args):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _set = {}
        document_data = document_info['datas']
        for _data in args:
            column = _data
            value = args[_data]
            document_data.update({
                column: value
            })

        _, error = verifier.update_document({'set': {"datas": json.dumps(document_data)}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_DATA_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def delete_document_data_by_document_id(document_id, field_id):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _set = {}
        document_data = document_info['datas']
        if field_id in document_data:
            del document_data[field_id]
        _, error = verifier.update_document({'set': {"datas": json.dumps(document_data)}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_DATA_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def delete_documents_by_document_id(document_id):
    if 'docservers' in current_context:
        docservers = current_context.docservers
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        docservers = _vars[9]

    document, error = verifier.get_document_by_id({'document_id': document_id})
    if not error:
        delete_documents(docservers, document['path'], document['filename'], document['full_jpg_filename'])

    _, error = verifier.update_document({
        'set': {"status": 'DEL'},
        'document_id': document_id
    })
    return '', 200


def delete_document_position_by_document_id(document_id, field_id):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _set = {}
        document_positions = document_info['positions']
        if field_id in document_positions:
            del document_positions[field_id]
        _, error = verifier.update_document(
            {'set': {"positions": json.dumps(document_positions)}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_POSITIONS_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def delete_document_page_by_document_id(document_id, field_id):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _set = {}
        document_pages = document_info['pages']
        if field_id in document_pages:
            del document_pages[field_id]
        _, error = verifier.update_document({'set': {"pages": json.dumps(document_pages)}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_PAGES_ERROR'),
                "message": gettext(error)
            }
            return response, 400


def delete_document(document_id):
    _, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _, error = verifier.update_document({'set': {'status': 'DEL'}, 'document_id': document_id})
        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('DELETE_DOCUMENT_ERROR'),
                "message": gettext(error)
            }
            return response, 400
    else:
        response = {
            "errors": gettext('DELETE_DOCUMENT_ERROR'),
            "message": gettext(error)
        }
        return response, 400


def update_document(document_id, data):
    _, error = verifier.get_document_by_id({'document_id': document_id})
    if error is None:
        _, error = verifier.update_document({'set': data, 'document_id': document_id})

        if error is None:
            return '', 200
        else:
            response = {
                "errors": gettext('UPDATE_DOCUMENT_ERROR'),
                "message": gettext(error)
            }
            return response, 400
    else:
        response = {
            "errors": gettext('UPDATE_DOCUMENT_ERROR'),
            "message": gettext(error)
        }
        return response, 400


def remove_lock_by_user_id(user_id):
    _, error = verifier.update_documents({
        'set': {"locked": False},
        'where': ['locked_by = %s'],
        'data': [user_id]
    })

    if error is None:
        return '', 200
    else:
        response = {
            "errors": gettext('REMOVE_LOCK_BY_USER_ID_ERROR'),
            "message": gettext(error)
        }
        return response, 400


def export_mem(document_id, data):
    if 'regex' in current_context and 'database' in current_context and 'log' in current_context:
        log = current_context.log
        regex = current_context.regex
        database = current_context.database
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        log = _vars[5]
        regex = _vars[2]
        database = _vars[0]
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if not error:
        return verifier_exports.export_mem(data['data'], document_info, log, regex, database)


def export_xml(document_id, data):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})

    if not error:
        if 'regex' in current_context and 'database' in current_context and 'log' in current_context:
            log = current_context.log
            regex = current_context.regex
            database = current_context.database
        else:
            custom_id = retrieve_custom_from_url(request)
            _vars = create_classes_from_custom_id(custom_id)
            log = _vars[5]
            regex = _vars[2]
            database = _vars[0]
        return verifier_exports.export_xml(data['data'], log, regex, document_info, database)


def export_pdf(document_id, data):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if not error:
        if 'configurations' in current_context and 'log' in current_context and 'regex' in current_context:
            log = current_context.log
            regex = current_context.regex
            configurations = current_context.configurations
        else:
            custom_id = retrieve_custom_from_url(request)
            _vars = create_classes_from_custom_id(custom_id)
            log = _vars[5]
            regex = _vars[2]
            configurations = _vars[10]
        return verifier_exports.export_pdf(data['data'], log, regex, document_info, configurations['locale'],
                                           data['compress_type'], data['ocrise'])


def export_facturx(document_id, data):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if not error:
        if 'configurations' in current_context and 'log' in current_context and 'regex' in current_context:
            log = current_context.log
            regex = current_context.regex
            configurations = current_context.configurations
        else:
            custom_id = retrieve_custom_from_url(request)
            _vars = create_classes_from_custom_id(custom_id)
            log = _vars[5]
            regex = _vars[2]
        return verifier_exports.export_facturx(data['data'], log, regex, document_info)


def ocr_on_the_fly(file_name, selection, thumb_size, positions_masks, lang):
    if 'files' in current_context and 'ocr' in current_context and 'docservers' in current_context:
        files = current_context.files
        ocr = current_context.ocr
        docservers = current_context.docservers
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        ocr = _vars[4]
        files = _vars[3]
        docservers = _vars[9]

    path = docservers['VERIFIER_IMAGE_FULL'] + '/' + file_name

    if positions_masks:
        path = docservers['VERIFIER_POSITIONS_MASKS'] + '/' + file_name

    text = files.ocr_on_fly(path, selection, ocr, thumb_size, lang=lang)
    if text:
        return text
    else:
        files.improve_image_detection(path)
        text = files.ocr_on_fly(path, selection, ocr, thumb_size, lang=lang)
        return text


def get_thumb_by_document_id(document_id):
    document_info, error = verifier.get_document_by_id({'document_id': document_id})
    if not error:
        register_date = pd.to_datetime(document_info['register_date'])
        year = register_date.strftime('%Y')
        month = register_date.strftime('%m')
        year_and_month = year + '/' + month
        return get_file_content('full', document_info['full_jpg_filename'], 'image/jpeg', year_and_month=year_and_month)
    else:
        return '', 404


def get_file_content(file_type, filename, mime_type, compress=False, year_and_month=False):
    if 'docservers' in current_context:
        docservers = current_context.docservers
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        docservers = _vars[9]

    content = False
    path = ''

    if file_type == 'full':
        path = docservers['VERIFIER_IMAGE_FULL']
        if year_and_month:
            path = path + '/' + year_and_month + '/'
    elif file_type == 'positions_masks':
        path = docservers['VERIFIER_POSITIONS_MASKS']
    elif file_type == 'referential_supplier':
        path = docservers['REFERENTIALS_PATH']

    if path and filename:
        full_path = path + '/' + filename
        if os.path.isfile(full_path):
            if compress and mime_type == 'image/jpeg':
                thumb_path = docservers['VERIFIER_THUMB']
                if year_and_month:
                    thumb_path = thumb_path + '/' + year_and_month + '/'
                if os.path.isfile(thumb_path + '/' + filename):
                    with open(thumb_path + '/' + filename, 'rb') as file:
                        content = file.read()
            else:
                with open(full_path, 'rb') as file:
                    content = file.read()
    if not content:
        if mime_type == 'image/jpeg':
            with open(docservers['PROJECT_PATH'] + '/dist/assets/not_found/document_not_found.jpg', 'rb') as file:
                content = file.read()
        else:
            with open(docservers['PROJECT_PATH'] + '/dist/assets/not_found/document_not_found.pdf', 'rb') as file:
                content = file.read()
    return Response(content, mimetype=mime_type)


def get_token_insee():
    if 'config' in current_context:
        config = current_context.config
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        config = _vars[1]

    credentials = base64.b64encode(
        (config['API']['siret-consumer'] + ':' + config['API']['siret-secret']).encode('UTF-8')).decode('UTF-8')

    try:
        res = requests.post(config['API']['siret-url-token'], data={'grant_type': 'client_credentials'},
                            headers={"Authorization": f"Basic {credentials}"}, timeout=5)
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
        return 'ERROR : ' + gettext('API_INSEE_ERROR_CONNEXION'), 201

    if 'Maintenance - INSEE' in res.text or res.status_code != 200:
        return 'ERROR : ' + gettext('API_INSEE_ERROR_CONNEXION'), 201
    else:
        return json.loads(res.text)['access_token'], 200


def verify_siren(token, siren):
    if 'config' in current_context:
        config = current_context.config
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        config = _vars[1]

    try:
        res = requests.get(config['API']['siren-url'] + siren,
                           headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
        return 'ERROR : ' + gettext('API_INSEE_ERROR_CONNEXION'), 201

    _return = json.loads(res.text)
    if 'header' not in res.text:
        return _return['fault']['message'], 201
    else:
        return _return['header']['message'], 200


def verify_siret(token, siret):
    if 'config' in current_context and 'log' in current_context:
        log = current_context.log
        config = current_context.config
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        config = _vars[1]
        log = _vars[5]

    try:
        res = requests.get(config['API']['siret-url'] + siret,
                           headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as _e:
        log.error(gettext('API_INSEE_ERROR_CONNEXION') + ' : ' + str(_e))
        return 'ERROR : ' + gettext('API_INSEE_ERROR_CONNEXION'), 201

    _return = json.loads(res.text)
    if 'header' not in res.text:
        return _return['fault']['message'], 201
    else:
        return _return['header']['message'], 200


def verify_vat_number(vat_number):
    if 'config' in current_context and 'log' in current_context:
        log = current_context.log
        config = current_context.config
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        config = _vars[1]
        log = _vars[5]
    url = config['API']['tva-url']
    country_code = vat_number[:2]
    vat_number = vat_number[2:]

    logging.getLogger('zeep').setLevel(logging.ERROR)
    try:
        client = Client(url)
        res = client.service.checkVat(country_code, vat_number)
        text = res['valid']
        if res['valid'] is False:
            text = gettext('VAT_NOT_VALID')
            return text, 400
        return text, 200
    except (exceptions.Fault, requests.exceptions.SSLError, requests.exceptions.ConnectionError,
            zeep.exceptions.XMLSyntaxError) as _e:
        log.error(gettext('VAT_API_ERROR') + ' : ' + str(_e))
        return gettext('VAT_API_ERROR'), 201


def get_totals(status, user_id, form_id):
    totals = {}
    allowed_customers, _ = user.get_customers_by_user_id(user_id)
    allowed_customers.append(0)  # Update allowed customers to add Unspecified customers

    totals['today'], error = verifier.get_totals({
        'time': 'today', 'status': status, 'form_id': form_id, 'allowedCustomers': allowed_customers
    })
    totals['yesterday'], error = verifier.get_totals({
        'time': 'yesterday', 'status': status, 'form_id': form_id, 'allowedCustomers': allowed_customers
    })
    totals['older'], error = verifier.get_totals({
        'time': 'older', 'status': status, 'form_id': form_id, 'allowedCustomers': allowed_customers
    })

    if error is None:
        return totals, 200
    else:
        response = {
            "errors": gettext('GET_TOTALS_ERROR'),
            "message": gettext(error)
        }
        return response, 401


def update_status(args):
    for _id in args['ids']:
        document = verifier.get_document_by_id({'document_id': _id})
        if len(document[0]) < 1:
            response = {
                "errors": gettext('DOCUMENT_NOT_FOUND'),
                "message": gettext('DOCUMENT_ID_NOT_FOUND', id=_id)
            }
            return response, 400

    res = verifier.update_status(args)
    if res:
        return '', 200
    else:
        response = {
            "errors": gettext('UPDATE_STATUS_ERROR'),
            "message": gettext(res)
        }
        return response, 400


def get_unseen(user_id):
    user_customers = user.get_customers_by_user_id(user_id)
    user_customers[0].append(0)
    total_unseen = verifier.get_total_documents({
        'select': ['count(documents.id) as unseen'],
        'where': ["status = %s", "customer_id = ANY(%s)"],
        'data': ['NEW', user_customers[0]],
        'table': ['documents'],
    })[0]
    return total_unseen['unseen'], 200
