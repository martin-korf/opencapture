# This file is part of Open-Capture for Invoices.

# Open-Capture for Invoices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture for Invoices.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>
import json
import os
import uuid
import mimetypes
from src.backend.import_process import FindDate, FindFooter, FindInvoiceNumber, FindSupplier, FindCustom, \
    FindOrderNumber, FindDeliveryNumber, FindFooterRaw
from src.backend.import_classes import _Spreadsheet


def insert(args, files, config, database, datas, positions, pages, tiff_filename, full_jpg_filename, file, original_file, supplier_id, status, nb_pages):
    if files.isTiff == 'True':
        try:
            filename = os.path.splitext(files.custom_fileName_tiff)
            improved_img = filename[0] + '_improved' + filename[1]
            os.remove(files.custom_fileName_tiff)
            os.remove(improved_img)
        except FileNotFoundError:
            pass
        path = config.cfg['GLOBAL']['tiffpath'] + '/' + tiff_filename.replace('-%03d', '-001')
    else:
        try:
            filename = os.path.splitext(files.custom_fileName)
            improved_img = filename[0] + '_improved' + filename[1]
            os.remove(files.custom_fileName)
            os.remove(improved_img)
        except FileNotFoundError:
            pass
        path = config.cfg['GLOBAL']['fullpath'] + '/' + full_jpg_filename.replace('-%03d', '-001')

    invoice_data = {
        'supplier_id': supplier_id,
        'filename': os.path.basename(file),
        'path': os.path.dirname(file),
        'img_width': str(files.get_size(path)),
        'full_jpg_filename': full_jpg_filename.replace('-%03d', '-001'),
        'tiff_filename': tiff_filename.replace('-%03d', '-001'),
        'original_filename': original_file,
        'positions': json.dumps(positions),
        'datas': json.dumps(datas),
        'pages': json.dumps(pages),
        'nb_pages': nb_pages,
        'status': status,
        'customer_id': 0
    }

    if 'input_id' in args:
        print(args['input_id'])
        input_settings = database.select({
            'select': ['*'],
            'table': ['inputs'],
            'where': ['input_id = %s'],
            'data': [args['input_id']],
        })

        if input_settings:
            if input_settings[0]['purchase_or_sale']:
                invoice_data.update({
                    'purchase_or_sale': input_settings[0]['purchase_or_sale']
                })
            if input_settings[0]['override_supplier_form']:
                invoice_data.update({
                    'form_id': input_settings[0]['default_form_id']
                })
            if input_settings[0]['customer_id']:
                invoice_data.update({
                    'customer_id': input_settings[0]['customer_id']
                })

    database.insert({
        'table': 'invoices',
        'columns': invoice_data
    })


def convert(file, files, ocr, nb_pages, custom_pages=False):
    if custom_pages:
        if files.isTiff == 'True':
            try:
                filename = os.path.splitext(files.custom_fileName_tiff)
                improved_img = filename[0] + '_improved' + filename[1]
                os.remove(files.custom_fileName_tiff)
                os.remove(improved_img)
            except FileNotFoundError:
                pass
            files.pdf_to_tiff(file, files.custom_fileName_tiff, open_img=False, last_page=nb_pages)
        else:
            try:
                filename = os.path.splitext(files.custom_fileName)
                improved_img = filename[0] + '_improved' + filename[1]
                os.remove(files.custom_fileName)
                os.remove(improved_img)
            except FileNotFoundError:
                pass
            files.pdf_to_jpg(file + '[' + str(int(nb_pages - 1)) + ']', open_img=False, is_custom=True)
    else:
        if files.isTiff == 'True':
            files.pdf_to_tiff(file, files.tiffName, True, True, True, 'header')
            ocr.header_text = ocr.line_box_builder(files.img)
            files.pdf_to_tiff(file, files.tiffName, True, True, True, 'footer')
            ocr.footer_text = ocr.line_box_builder(files.img)
            files.pdf_to_tiff(file, files.tiffName, True)
            ocr.text = ocr.line_box_builder(files.img)
            if nb_pages > 1:
                files.pdf_to_tiff(file, files.tiffName_last, False, True, True, 'header', nb_pages)
                ocr.header_last_text = ocr.line_box_builder(files.img)
                files.pdf_to_tiff(file, files.tiffName_last, False, True, True, 'footer', nb_pages)
                ocr.footer_last_text = ocr.line_box_builder(files.img)
                files.pdf_to_tiff(file, files.tiffName_last, last_page=nb_pages)
                ocr.last_text = ocr.line_box_builder(files.img)
        else:
            files.pdf_to_jpg(file + '[0]', True, True, 'header')
            ocr.header_text = ocr.line_box_builder(files.img)
            files.pdf_to_jpg(file + '[0]', True, True, 'footer')
            ocr.footer_text = ocr.line_box_builder(files.img)
            files.pdf_to_jpg(file + '[0]')
            ocr.text = ocr.line_box_builder(files.img)
            if nb_pages > 1:
                files.pdf_to_jpg(file + '[' + str(nb_pages - 1) + ']', True, True, 'header', True)
                ocr.header_last_text = ocr.line_box_builder(files.img)
                files.pdf_to_jpg(file + '[' + str(nb_pages - 1) + ']', True, True, 'footer', True)
                ocr.footer_last_text = ocr.line_box_builder(files.img)
                files.pdf_to_jpg(file + '[' + str(nb_pages - 1) + ']', last_image=True)
                ocr.last_text = ocr.line_box_builder(files.img)


def update_typo_database(database, vat_number, typo, log, config):
    spreadsheet = _Spreadsheet(log, config)
    mime = mimetypes.guess_type(spreadsheet.referencialSuppplierSpreadsheet)[0]
    if mime in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        spreadsheet.write_typo_excel_sheet(vat_number, typo)
    else:
        spreadsheet.write_typo_ods_sheet(vat_number, typo)

    database.update({
        'table': ['suppliers'],
        'set': {
            'typology': typo,
        },
        'where': ['vat_number = %s'],
        'data': [vat_number]
    })


def process(args, file, log, config, files, ocr, locale, database, typo):
    log.info('Processing file : ' + file)
    datas = {}
    pages = {}
    positions = {}
    # get the number of pages into the PDF documents
    nb_pages = files.get_pages(file, config)
    splitted_file = os.path.basename(file).split('_')
    if splitted_file[0] == 'SPLITTER':
        original_file = os.path.basename(file).split('_')
        original_file = original_file[1] + '_' + original_file[2] + '.pdf'
    else:
        original_file = os.path.basename(file)

    # Convert files to JPG or TIFF
    convert(file, files, ocr, nb_pages)

    # Find supplier in document
    supplier = FindSupplier(ocr, log, locale, database, files, nb_pages, 1, False).run()

    i = 0
    tmp_nb_pages = nb_pages
    while not supplier:
        tmp_nb_pages = tmp_nb_pages - 1
        if i == 3 or int(tmp_nb_pages) == 1 or nb_pages == 1:
            break

        convert(file, files, ocr, tmp_nb_pages, True)
        supplier = FindSupplier(ocr, log, locale, database, files, nb_pages, tmp_nb_pages, True).run()
        i += 1

    if supplier:
        datas.update({
            'name': supplier[2]['name'],
            'vat_number': supplier[2]['vat_number'],
            'siret': supplier[2]['siret'],
            'siren': supplier[2]['siren'],
            'address1': supplier[2]['address1'],
            'address2': supplier[2]['address2'],
            'postal_code': supplier[2]['postal_code'],
            'city': supplier[2]['city'],
            'country': supplier[2]['country'],
        })

    if typo:
        update_typo_database(database, supplier[0], typo, log, config)

    # Find custom informations using mask
    custom_fields = FindCustom(ocr.header_text, log, locale, config, ocr, files, supplier, typo, file).run()
    columns = {}
    if custom_fields:
        for field in custom_fields:
            field_name = field.split('-')[1]
            field_name_position = field_name + '_position'
            columns.update({
                field_name: custom_fields[field][0],
                field_name_position: str(custom_fields[field][1])
            })

    # Find invoice number
    invoice_number_class = FindInvoiceNumber(ocr, files, log, locale, config, database, supplier, file, typo, ocr.header_text, 1, False, ocr.footer_text)
    invoice_number = invoice_number_class.run()
    if not invoice_number:
        invoice_number_class.text = ocr.header_last_text
        invoice_number_class.footer_text = ocr.footer_last_text
        invoice_number_class.nbPages = nb_pages
        invoice_number_class.customPage = True
        invoice_number = invoice_number_class.run()
        if invoice_number:
            invoice_number.append(nb_pages)

    j = 0
    tmp_nb_pages = nb_pages
    invoice_found_on_first_or_last_page = False
    while not invoice_number:
        tmp_nb_pages = tmp_nb_pages - 1
        if j == 3 or int(tmp_nb_pages) - 1 == 0 or nb_pages == 1:
            break
        convert(file, files, ocr, tmp_nb_pages, True)

        if files.isTiff == 'True':
            _file = files.custom_fileName_tiff
        else:
            _file = files.custom_fileName

        image = files.open_image_return(_file)

        invoice_number_class.text = ocr.line_box_builder(image)
        invoice_number_class.nbPages = tmp_nb_pages
        invoice_number_class.customPage = True

        invoice_number = invoice_number_class.run()
        if invoice_number:
            invoice_found_on_first_or_last_page = True
        j += 1

    if invoice_number:
        datas.update({'invoice_number': invoice_number[0]})
        if invoice_number[1]:
            positions.update({'invoice_number': files.reformat_positions(invoice_number[1])})
        if invoice_number[2]:
            pages.update({'invoice_number': invoice_number[2]})

    # Find invoice date number
    if invoice_found_on_first_or_last_page:
        log.info("Search invoice date using the same page as invoice number")
        text_custom = invoice_number_class.text
        page_for_date = tmp_nb_pages
    else:
        text_custom = ocr.text
        page_for_date = 1

    date = FindDate(text_custom, log, locale, config, files, ocr, supplier, typo, page_for_date, database, file).run()
    if date:
        datas.update({'invoice_date': date[0]})
        if date[1]:
            positions.update({'invoice_date': files.reformat_positions(date[1])})
        if date[2]:
            pages.update({'invoice_date': date[2]})

        if date[3]:
            datas.update({'invoice_due_date': date[3][0]})
            pages.update({'invoice_due_date': date[2]})
            if len(date[3]) > 1:
                positions.update({'invoice_due_date': files.reformat_positions(date[3][1])})

    # Find footer informations (total amount, no rate amount etc..)
    footer_class = FindFooter(ocr, log, locale, config, files, database, supplier, file, ocr.footer_text, typo)
    if supplier and supplier[2]['get_only_raw_footer'] == 'True':
        footer_class = FindFooterRaw(ocr, log, locale, config, files, database, supplier, file, ocr.footer_text, typo)

    footer = footer_class.run()
    if not footer:
        footer_class.target = 'full'
        footer_class.text = ocr.last_text
        footer_class.nbPage = nb_pages
        footer = footer_class.run()
        if footer:
            if len(footer) == 4:
                footer[3] = nb_pages
            else:
                footer.append(nb_pages)
        i = 0
        tmp_nb_pages = nb_pages
        while not footer:
            tmp_nb_pages = tmp_nb_pages - 1
            if i == 3 or int(tmp_nb_pages) == 1 or nb_pages == 1:
                break
            convert(file, files, ocr, tmp_nb_pages, True)
            if files.isTiff == 'True':
                _file = files.custom_fileName_tiff
            else:
                _file = files.custom_fileName

            image = files.open_image_return(_file)
            text = ocr.line_box_builder(image)
            footer_class.text = text
            footer_class.target = 'full'
            footer_class.nbPage = tmp_nb_pages
            footer = footer_class.run()
            i += 1

    if footer:
        if footer[0]:
            datas.update({'no_rate_amount': footer[0][0]})
            datas.update({'total_ht': footer[0][0]})
            if len(footer[0]) > 1:
                positions.update({'no_rate_amount': files.reformat_positions(footer[0][1])})
                if footer[3]:
                    pages.update({'no_rate_amount': footer[3]})
        if footer[1]:
            datas.update({'total_ttc': footer[1][0]})
            if len(footer[1]) > 1:
                positions.update({'total_ttc': files.reformat_positions(footer[1][1])})
                if footer[3]:
                    pages.update({'total_ttc': footer[3]})
        if footer[2]:
            datas.update({'vat_rate': footer[2][0]})
            if len(footer[2]) > 1:
                positions.update({'vat_rate': files.reformat_positions(footer[2][1])})
                if footer[3]:
                    pages.update({'vat_rate': footer[3]})
        if footer[4]:
            datas.update({'vat_amount': footer[4][0]})
            datas.update({'total_vat': footer[4][0]})
            if len(footer[4]) > 1:
                positions.update({'vat_amount': files.reformat_positions(footer[4][1])})
                if footer[3]:
                    pages.update({'vat_amount': footer[3]})

    # Find delivery number
    delivery_number_class = FindDeliveryNumber(ocr, files, log, locale, config, database, supplier, file, typo, ocr.header_text, 1, False)
    delivery_number = delivery_number_class.run()
    if not delivery_number:
        delivery_number_class.text = ocr.footer_text
        delivery_number_class.target = 'footer'
        delivery_number = delivery_number_class.run()

    if delivery_number:
        datas.update({'delivery_number': delivery_number[0]})
        if delivery_number[1]:
            positions.update({'delivery_number': files.reformat_positions(delivery_number[1])})
        if delivery_number[2]:
            pages.update({'delivery_number': delivery_number[2]})

    # Find order number
    order_number_class = FindOrderNumber(ocr, files, log, locale, config, database, supplier, file, typo, ocr.header_text, 1, False)
    order_number = order_number_class.run()
    if not order_number:
        order_number_class.text = ocr.footer_text
        order_number_class.target = 'footer'
        order_number = order_number_class.run()

    if order_number:
        datas.update({'order_number': order_number[0]})
        if order_number[1]:
            positions.update({'order_number': files.reformat_positions(order_number[1])})
        if order_number[2]:
            pages.update({'order_number': order_number[2]})

    file_name = str(uuid.uuid4())
    full_jpg_filename = 'full_' + file_name + '-%03d.jpg'
    tiff_filename = 'tiff_' + file_name + '-%03d.tiff'

    file = files.move_to_docservers(config.cfg, file)
    # Convert all the pages to JPG (used to full web interface)
    files.save_img_with_wand(file, config.cfg['GLOBAL']['fullpath'] + '/' + full_jpg_filename)
    # If tiff support enabled, save all the pages to TIFF (used for OCR ON FLY)
    if files.isTiff == 'True':
        files.save_pdf_to_tiff_in_docserver(file, config.cfg['GLOBAL']['tiffpath'] + '/' + tiff_filename)

    # If all informations are found, do not send it to GED
    if supplier and supplier[2]['skip_auto_validate'] == 'False' and date and invoice_number and footer and config.cfg['GLOBAL']['allowautomaticvalidation'] == 'True':
        log.info('All the usefull informations are found. Export the XML and end process')
        insert(args, files, config, database, datas, positions, pages, tiff_filename, full_jpg_filename, file, original_file, supplier[2]['supplier_id'], 'END', nb_pages)
    else:
        insert(args, files, config, database, datas, positions, pages, tiff_filename, full_jpg_filename, file, original_file, supplier[2]['supplier_id'], 'NEW', nb_pages)
        if supplier and supplier[2]['skip_auto_validate'] == 'True':
            log.info('Skip automatic validation for this supplier this time')
            database.update({
                'table': ['accounts_suppliers'],
                'set': {
                    'skip_auto_validate': 'False'
                },
                'where': ['vat_number = %s'],
                'data': [supplier[2]['vat_number']]
            })

    return True
