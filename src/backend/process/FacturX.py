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
import re
import json
import uuid
import facturx
import datetime
from unidecode import unidecode
from xml.etree import ElementTree as Et
from src.backend import verifier_exports
from src.backend.functions import delete_documents

###
# FACTUREX_CORRESPONDANCE is used to convert XML data to Open-Capture data
# The options are:
#   - id: the tag containing the information
#   - tagParent: the parent tag of the tag containing the information (if the tag name is not unique)
#   - attribTag: the attribute name containing specific information
#   - attribValue: the value of the attribute name.
#       This is used to find information if same tag is used to differents values (ex: VAT number and Tax number)
###

FACTUREX_CORRESPONDANCE = {
    'facturation': {
        'total_vat': {'id': 'TaxTotalAmount'},
        'total_ttc': {'id': 'GrandTotalAmount'},
        'currency': {'id': 'InvoiceCurrencyCode'},
        'total_ht': {'id': 'TaxBasisTotalAmount'},
        'note': {'id': 'Content', 'tagParent': 'IncludedNote'},
        'date': {'id': 'DateTimeString', 'tagParent': 'IssueDateTime'},
        'invoice_number': {'id': 'ID', 'tagParent': 'ExchangedDocument'},
        'due_date': {'id': 'DateTimeString', 'tagParent': 'DueDateDateTime'},
        'order_number': {'id': 'IssuerAssignedID', 'tagParent': 'BuyerOrderReferencedDocument'},
        'contract_reference': {'id': 'IssuerAssignedID', 'tagParent': 'ContractReferencedDocument'}
    },
    'payment': {
        'reference': {'id': 'PaymentReference'},
        'iban': {'id': 'IBANID', 'tagParent': 'PayeePartyCreditorFinancialAccount'},
        'conditions': {'id': 'Description', 'tagParent': 'SpecifiedTradePaymentTerms'},
        'bic': {'id': 'BICID', 'tagParent': 'PayeeSpecifiedCreditorFinancialInstitution'},
        'type_code': {'id': 'TypeCode', 'tagParent': 'SpecifiedTradeSettlementPaymentMeans'},
        'informations': {'id': 'Information', 'tagParent': 'SpecifiedTradeSettlementPaymentMeans'}
    },
    'taxes': {
        'type_code': {'id': 'TypeCode',  'tagParent': 'ApplicableTradeTax'},
        'no_rate_amount': {'id': 'BasisAmount',  'tagParent': 'ApplicableTradeTax'},
        'category_code': {'id': 'CategoryCode', 'tagParent': 'ApplicableTradeTax'},
        'vat_amount': {'id': 'CalculatedAmount', 'tagParent': 'ApplicableTradeTax'},
        'vat_rate': {'id': 'RateApplicablePercent', 'tagParent': 'ApplicableTradeTax'}
    },
    'facturation_lines': {
        'name': {'id': 'Name'},
        'product_id': {'id': 'GlobalID'},
        'quantity': {'id': 'BilledQuantity'},
        'trade_tax_type_code': {'id': 'TypeCode'},
        'seller_assigned_id': {'id': 'SellerAssignedID'},
        'trade_tax_category_code': {'id': 'CategoryCode'},
        'vat_rate': {'id': 'RateApplicablePercent'},
        'value': {'id': 'Value', 'tagParent': 'ApplicableProductCharacteristic'},
        'allowance_reason': {'id': 'Reason', 'tagParent': 'AppliedTradeAllowanceCharge'},
        'unit_price_ht': {'id': 'ChargeAmount', 'tagParent': 'NetPriceProductTradePrice'},
        'gross_price_ht': {'id': 'ChargeAmount', 'tagParent': 'GrossPriceProductTradePrice'},
        'description': {'id': 'Description', 'tagParent': 'ApplicableProductCharacteristic'},
        'allowance_amount': {'id': 'ActualAmount', 'tagParent': 'AppliedTradeAllowanceCharge'},
        'no_rate_amount': {'id': 'LineTotalAmount', 'tagParent': 'SpecifiedTradeSettlementLineMonetarySummation'}
    },
    'supplier': {
        'global_id': {'id': 'GlobalID'},
        'name': {'id': 'Name'},
        'number': {'id': 'ID', 'tagParent': 'SellerTradeParty'},
        'siret': {'id': 'ID', 'tagParent': 'SpecifiedLegalOrganization'},
        'vat_number': {'id': 'ID', 'attribTag': 'schemeID', 'attribValue': 'VA'},
        'tax_number': {'id': 'ID', 'attribTag': 'schemeID', 'attribValue': 'FC'}
    },
    'buyer': {
        'buyer_name': {'id': 'Name'},
        'number': {'id': 'ID', 'tagParent': 'BuyerTradeParty'},
        'vat_number': {'id': 'ID', 'attribTag': 'schemeID', 'attribValue': 'VA'},
        'tax_number': {'id': 'ID', 'attribTag': 'schemeID', 'attribValue': 'FC'},
        'siret': {'id': 'ID', 'tagParent': 'SpecifiedLegalOrganization'}
    },
    'supplier_trade_contact': {
        'email': {'id': 'URIID'},
        'name': {'id': 'PersonName'},
        'phone': {'id': 'CompleteNumber'}
    },
    'buyer_trade_contact': {
        'email': {'id': 'URIID'},
        'name': {'id': 'PersonName'},
        'phone': {'id': 'CompleteNumber'}
    },
    'supplier_address': {
        'city': {'id': 'CityName'},
        'address1': {'id': 'LineOne'},
        'address2': {'id': 'LineTwo'},
        'country': {'id': 'CountryID'},
        'postal_code': {'id': 'PostcodeCode'}
    },
    'buyer_address': {
        'city': {'id': 'CityName'},
        'address1': {'id': 'LineOne'},
        'address2': {'id': 'LineTwo'},
        'country': {'id': 'CountryID'},
        'postal_code': {'id': 'PostcodeCode'}
    }
}

###
# FACTUREX_DATA array is used to find various information in the PDF xml content
# Each array is composed of a list of path to find the information
# Each list start with lower path possible and then each element is a child of the previous element
# The last element of the list is the tag containing the information
###

NAMESPACE = '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}'
FACTUREX_DATA = {
    'notes': [
        [
            './/' + NAMESPACE + 'IncludedNote'
        ]
    ],
    'facturation': [
        [
            './/' + NAMESPACE + 'IssueDateTime'
        ],
        [
            './/{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}ExchangedDocument',
            NAMESPACE + 'ID'
        ],
        [
            './/' + NAMESPACE + 'BuyerOrderReferencedDocument'
        ],
        [
            './/' + NAMESPACE + 'ContractReferencedDocument'
        ],
        [
            './/' + NAMESPACE + 'ApplicableHeaderTradeSettlement',
            './/' + NAMESPACE + 'SpecifiedTradeSettlementHeaderMonetarySummation'
        ],
        [
            './/' + NAMESPACE + 'ApplicableHeaderTradeSettlement',
            './/' + NAMESPACE + 'SpecifiedTradePaymentTerms',
            './/' + NAMESPACE + 'DueDateDateTime'
        ]
    ],
    'payment': [
        [
            './/' + NAMESPACE + 'ApplicableHeaderTradeSettlement',
            './/' + NAMESPACE + 'SpecifiedTradeSettlementPaymentMeans',
            './/' + NAMESPACE + 'PayeePartyCreditorFinancialAccount'
        ],
        [
            './/' + NAMESPACE + 'ApplicableHeaderTradeSettlement',
            './/' + NAMESPACE + 'SpecifiedTradeSettlementPaymentMeans',
            './/' + NAMESPACE + 'PayeeSpecifiedCreditorFinancialInstitution'
        ],
        [
            './/' + NAMESPACE + 'ApplicableHeaderTradeSettlement',
            './/' + NAMESPACE + 'SpecifiedTradePaymentTerms'
        ]
    ],
    'facturation_lines': [
        [
            './/' + NAMESPACE + 'IncludedSupplyChainTradeLineItem'
        ]
    ],
    'supplier_trade_contact': [
        [
            './/' + NAMESPACE + 'SellerTradeParty',
            NAMESPACE + 'DefinedTradeContact',
            NAMESPACE + 'EmailURIUniversalCommunication'
        ],
        [
            './/' + NAMESPACE + 'SellerTradeParty',
            NAMESPACE + 'DefinedTradeContact',
            './/' + NAMESPACE + 'TelephoneUniversalCommunication'
        ],
        [
            NAMESPACE + 'SellerTradeParty'
        ]
    ],
    'buyer_trade_contact': [
        [
            './/' + NAMESPACE + 'BuyerTradeParty',
            NAMESPACE + 'DefinedTradeContact',
            NAMESPACE + 'EmailURIUniversalCommunication'
        ],
        [
            './/' + NAMESPACE + 'BuyerTradeParty',
            NAMESPACE + 'DefinedTradeContact',
            './/' + NAMESPACE + 'TelephoneUniversalCommunication'
        ]
    ],
    'supplier': [
        [
            './/' + NAMESPACE + 'SellerTradeParty',
            './/' + NAMESPACE + 'SpecifiedTaxRegistration'
        ],
        [
            './/' + NAMESPACE + 'SellerTradeParty',
            './/' + NAMESPACE + 'SpecifiedLegalOrganization'
        ]
    ],
    'buyer': [
        [
            './/' + NAMESPACE + 'BuyerTradeParty',
            './/' + NAMESPACE + 'SpecifiedTaxRegistration'
        ],
        [
            './/' + NAMESPACE + 'BuyerTradeParty',
            './/' + NAMESPACE + 'SpecifiedLegalOrganization'
        ]
    ],
    'supplier_address': [
        [
            './/' + NAMESPACE + 'SellerTradeParty',
            './/' + NAMESPACE + 'PostalTradeAddress'
        ]
    ],
    'buyer_address': [
        [
            './/' + NAMESPACE + 'BuyerTradeParty',
            './/' + NAMESPACE + 'PostalTradeAddress'
        ]
    ]
}

COUNTRY_CORRESPONDANCES = {
    'FR': 'France',
    'DE': 'Allemagne'
}


def fill_data(child, corrrespondance, parent):
    return_data = {}
    for data in child:
        tag = re.sub('{.*}', '', data.tag)
        for key in corrrespondance:
            if corrrespondance[key]['id'] == tag:
                if 'tagParent' in corrrespondance[key] and corrrespondance[key]['tagParent'] != parent:
                    continue
                if 'attribTag' in corrrespondance[key]:
                    for child_data in child:
                        attrib_tag = corrrespondance[key]['attribTag']
                        attrib_value = corrrespondance[key]['attribValue']
                        if attrib_tag in child_data.attrib and child_data.attrib[attrib_tag] == attrib_value:
                            return_data[key] = unidecode(child_data.text.strip())
                else:
                    return_data[key] = unidecode(data.text.strip())
    return return_data


def browse_xml(root, data_type, original_root, level=0, cpt=0, return_data=None):
    if return_data is None:
        return_data = {}
    if level > 0:
        root = original_root

    xml_tree = FACTUREX_DATA[data_type]

    if not root.findall(xml_tree[level][cpt]):
        if cpt < len(xml_tree[level]) - 1:
            return browse_xml(root, data_type, original_root, level, cpt + 1, return_data)
        elif level < len(xml_tree) - 1:
            return browse_xml(root, data_type, original_root, level + 1, 0, return_data)

    for child in root.findall(xml_tree[level][cpt]):
        parent = re.sub('{.*}', '', child.tag)
        return_data.update(fill_data(child, FACTUREX_CORRESPONDANCE[data_type], parent))
        if cpt < len(xml_tree[level]) - 1:
            return browse_xml(child, data_type, original_root, level, cpt + 1, return_data)
        elif level < len(xml_tree) - 1:
            return browse_xml(child, data_type, original_root, level + 1, 0, return_data)
    return return_data


def browse_xml_specific(root, grand_parent, parent):
    taxes = []
    correspondances = FACTUREX_CORRESPONDANCE['taxes']
    for child in root.findall('.//' + NAMESPACE + grand_parent):
        for specific in child.findall(NAMESPACE + parent):
            if specific.text.strip():
                taxes.append(unidecode(specific.text.strip()))
            else:
                taxes.append(fill_data(specific, correspondances, parent))
    return taxes


def browse_xml_lines(root):
    cpt = 1
    lines = {}
    correspondances = FACTUREX_CORRESPONDANCE['facturation_lines']

    for i in range(1, len(root.findall('.//' + NAMESPACE + 'IncludedSupplyChainTradeLineItem')) + 1):
        lines[i] = {
            'global': {},
            'unit_price': {},
            'allowances': [],
            'trade_taxes': {},
            'characteristics': {}
        }

    for child in root.findall('.//' + NAMESPACE + 'IncludedSupplyChainTradeLineItem'):
        for specified_trade in child.findall(NAMESPACE + 'SpecifiedTradeProduct'):
            lines[cpt]['global'].update(fill_data(specified_trade, correspondances, None))
            for product_char in specified_trade.findall('.//' + NAMESPACE + 'ApplicableProductCharacteristic'):
                parent = 'ApplicableProductCharacteristic'
                lines[cpt]['characteristics'].update(fill_data(product_char, correspondances, parent))

        for delivery in child.findall(NAMESPACE + 'SpecifiedLineTradeDelivery'):
            lines[cpt]['global'].update(fill_data(delivery, correspondances, None))
            for data in delivery:
                tag = re.sub('{.*}', '', data.tag)
                if tag == 'BilledQuantity':
                    lines[cpt]['global']['unit_type'] = data.attrib['unitCode']

        for prices in child.findall('.//' + NAMESPACE + 'SpecifiedLineTradeSettlement'):
            for trade_tax in prices.findall(NAMESPACE + 'ApplicableTradeTax'):
                lines[cpt]['trade_taxes'].update(fill_data(trade_tax, correspondances, None))
            for trade_tax in prices.findall(NAMESPACE + 'SpecifiedTradeSettlementLineMonetarySummation'):
                parent = 'SpecifiedTradeSettlementLineMonetarySummation'
                lines[cpt]['global'].update(fill_data(trade_tax, correspondances, parent))

        for specified_line in child.findall(NAMESPACE + 'SpecifiedLineTradeAgreement'):
            for product_char in specified_line.findall('.//' + NAMESPACE + 'NetPriceProductTradePrice'):
                lines[cpt]['unit_price'].update(fill_data(product_char, correspondances, 'NetPriceProductTradePrice'))
            for product_char in specified_line.findall('.//' + NAMESPACE + 'GrossPriceProductTradePrice'):
                lines[cpt]['unit_price'].update(fill_data(product_char, correspondances, 'GrossPriceProductTradePrice'))
                for allowances in product_char.findall('.//' + NAMESPACE + 'AppliedTradeAllowanceCharge'):
                    parent = 'AppliedTradeAllowanceCharge'
                    lines[cpt]['allowances'].append(fill_data(allowances, correspondances, parent))

        cpt += 1
    return lines


def insert(args):
    log = args['log']
    regex = args['regex']
    files = args['files']
    database = args['database']
    docservers = args['docservers']
    configurations = args['configurations']
    status = 'NEW'

    jpg_filename = str(uuid.uuid4())
    files.save_img_with_pdf2image(args['file'], docservers['VERIFIER_IMAGE_FULL'] + '/' + jpg_filename, docservers=True)
    files.save_img_with_pdf2image_min(args['file'], docservers['VERIFIER_THUMB'] + '/' + jpg_filename)

    year = datetime.datetime.now().strftime('%Y')
    month = datetime.datetime.now().strftime('%m')
    year_and_month = year + '/' + month
    path = docservers['VERIFIER_IMAGE_FULL'] + '/' + year_and_month + '/' + jpg_filename + '-001.jpg'
    nb_pages = files.get_pages(docservers, args['file'])
    splitted_file = os.path.basename(args['file']).split('_')
    if splitted_file[0] == 'SPLITTER':
        original_file = os.path.basename(args['file']).split('_')
        original_file = original_file[1] + '_' + original_file[2] + '.pdf'
    else:
        original_file = os.path.basename(args['file'])

    invoice_data = {
        'facturx': True,
        'status': status,
        'customer_id': 0,
        'nb_pages': nb_pages,
        'path': os.path.dirname(path),
        'datas': json.dumps(args['datas']),
        'original_filename': original_file,
        'img_width': str(files.get_width(path)),
        'filename': os.path.basename(args['file']),
        'full_jpg_filename': jpg_filename + '-001.jpg',
        'facturx_level': args['facturx_level'].upper(),
    }

    if 'supplier_id' in args and args['supplier_id']:
        invoice_data['supplier_id'] = args['supplier_id']

    if args.get('isMail') is None or args.get('isMail') is False:
        if 'input_id' in args and args['input_id']:
            input_settings = database.select({
                'select': ['*'],
                'table': ['inputs'],
                'where': ['input_id = %s', 'module = %s'],
                'data': [args['input_id'], 'verifier'],
            })
            if input_settings:
                input_settings = input_settings[0]
                if input_settings['purchase_or_sale']:
                    invoice_data.update({
                        'purchase_or_sale': input_settings['purchase_or_sale']
                    })
                if input_settings['customer_id']:
                    invoice_data.update({
                        'customer_id': input_settings['customer_id']
                    })
    else:
        if 'customer_id' in args and args['customer_id']:
            invoice_data.update({
                'customer_id': args['customer_id']
            })
        if 'form_id' in args and args['form_id']:
            invoice_data.update({
                'form_id': args['form_id']
            })

    if 'form_id' in args and args['form_id']:
        invoice_data.update({
            'form_id': args['form_id']
        })

    insert_invoice = True
    if status == 'END' and 'form_id' in invoice_data and invoice_data['form_id']:
        outputs = database.select({
            'select': ['outputs'],
            'table': ['form_models'],
            'where': ['id = %s'],
            'data': [invoice_data['form_id']],
        })

        if outputs:
            for output_id in outputs[0]['outputs']:
                output_info = database.select({
                    'select': ['output_type_id', 'data', 'compress_type', 'ocrise'],
                    'table': ['outputs'],
                    'where': ['id = %s'],
                    'data': [output_id]
                })
                if output_info:
                    if output_info[0]['output_type_id'] == 'export_xml':
                        verifier_exports.export_xml(output_info[0]['data'], log, regex, invoice_data, database)
                    elif output_info[0]['output_type_id'] == 'export_mem':
                        verifier_exports.export_mem(output_info[0]['data'], invoice_data, log, regex, database)
                    elif output_info[0]['output_type_id'] == 'export_pdf':
                        verifier_exports.export_pdf(output_info[0]['data'], log, regex, invoice_data,
                                                    configurations['locale'], output_info[0]['compress_type'],
                                                    output_info[0]['ocrise'])

            if 'form_id' in args and args['form_id']:
                form_settings = database.select({
                    'select': ['settings'],
                    'table': ['form_models'],
                    'where': ['id = %s'],
                    'data': [args['form_id']]
                })
                if 'delete_documents_after_outputs' in form_settings and form_settings['delete_documents_after_outputs']:
                    delete_documents(docservers, invoice_data['path'], invoice_data['filename'], jpg_filename)
                    insert_invoice = False
    res = False
    if insert_invoice:
        res = database.insert({
            'table': 'invoices',
            'columns': invoice_data
        })
    return res


def retrieve_data(array, key, regex=None):
    if key in ['date', 'due_date'] and regex:
        if key in array and array[key]:
            return datetime.datetime.strptime(array[key], '%Y%m%d').strftime(regex['format_date'])
    else:
        return array[key] if key in array and array[key] else ''


def create_supplier_and_address(database, supplier, address):
    country = address['country']
    if country in COUNTRY_CORRESPONDANCES and COUNTRY_CORRESPONDANCES[country]:
        country = COUNTRY_CORRESPONDANCES[country]
    args = {
        'table': 'addresses',
        'columns': {
            'address1': address['address1'] if 'address1' in address else '',
            'address2': address['address2'] if 'address2' in address else '',
            'postal_code': address['postal_code'] if 'postal_code' in address else '',
            'city': address['city'] if 'city' in address else '',
            'country': country,
        }
    }
    address_id = database.insert(args)
    if ('siren' not in supplier or not supplier['siren']) and 'siret' in supplier and supplier['siret']:
        supplier['siren'] = supplier['siret'][:9]

    args = {
        'table': 'accounts_supplier',
        'columns': {
            'vat_number': str(supplier['vat_number']),
            'name': supplier['name'],
            'siren': supplier['siren'] if 'siren' in supplier else '',
            'siret': supplier['siret'] if 'siret' in supplier else '',
            'address_id': str(address_id),
        }
    }
    return database.insert(args)


def supplier_exists(database, vat_number):
    res = database.select({
        'select': ['id'],
        'table': ['accounts_supplier'],
        'where': ['vat_number = %s'],
        'data': [vat_number]
    })
    return res


def process(args):
    root = Et.fromstring(args['xml_content'])
    del args['xml_content']

    args['facturx_data'] = {
        'buyer': browse_xml(root, 'buyer', root),
        'facturation_lines': browse_xml_lines(root),
        'payment': browse_xml(root, 'payment', root),
        'supplier': browse_xml(root, 'supplier', root),
        'facturation': browse_xml(root, 'facturation', root),
        'buyer_address': browse_xml(root, 'buyer_address', root),
        'notes': browse_xml_specific(root, 'IncludedNote', 'Content'),
        'supplier_address': browse_xml(root, 'supplier_address', root),
        'buyer_trade_contact': browse_xml(root, 'buyer_trade_contact', root),
        'supplier_trade_contact': browse_xml(root, 'supplier_trade_contact', root),
        'taxes': browse_xml_specific(root, 'ApplicableHeaderTradeSettlement', 'ApplicableTradeTax')
    }

    if args['facturx_data']['supplier'] and args['facturx_data']['supplier']['vat_number']:
        res = supplier_exists(args['database'], args['facturx_data']['supplier']['vat_number'])
        if not res:
            args['supplier_id'] = create_supplier_and_address(args['database'], args['facturx_data']['supplier'], args['facturx_data']['supplier_address'])
        else:
            args['supplier_id'] = res[0]['id']

    args['datas'] = {
        "city": retrieve_data(args['facturx_data']['supplier_address'], 'city'),
        "name": retrieve_data(args['facturx_data']['supplier'], 'name'),
        "siret": retrieve_data(args['facturx_data']['supplier'], 'siret'),
        "country": retrieve_data(args['facturx_data']['supplier_address'], 'country'),
        "address1": retrieve_data(args['facturx_data']['supplier_address'], 'address1'),
        "address2": retrieve_data(args['facturx_data']['supplier_address'], 'address2'),
        "total_ht": retrieve_data(args['facturx_data']['facturation'], 'total_ht'),
        "total_ttc": retrieve_data(args['facturx_data']['facturation'], 'total_ttc'),
        "total_vat": retrieve_data(args['facturx_data']['facturation'], 'total_vat'),
        "vat_number": retrieve_data(args['facturx_data']['supplier'], 'vat_number'),
        "postal_code": retrieve_data(args['facturx_data']['supplier_address'], 'postal_code'),
        "invoice_number": retrieve_data(args['facturx_data']['facturation'], 'invoice_number'),
        "quotation_number": retrieve_data(args['facturx_data']['facturation'], 'order_number'),
        "document_date": retrieve_data(args['facturx_data']['facturation'], 'date', args['regex']),
        "document_due_date": retrieve_data(args['facturx_data']['facturation'], 'due_date', args['regex']),
    }

    cpt_taxes = 0
    for taxes in args['facturx_data']['taxes']:
        index_rate = 'vat_rate' if cpt_taxes == 0 else 'vat_rate_' + str(cpt_taxes)
        index_amount = 'vat_amount' if cpt_taxes == 0 else 'vat_amount_' + str(cpt_taxes)
        index_ht = 'no_rate_amount' if cpt_taxes == 0 else 'no_rate_amount_' + str(cpt_taxes)

        args['datas'][index_rate] = taxes['vat_rate']
        args['datas'][index_ht] = taxes['no_rate_amount']
        args['datas'][index_amount] = taxes['vat_amount']
        cpt_taxes += 1

    cpt_lines = 0
    for lines in args['facturx_data']['facturation_lines']:
        line = args['facturx_data']['facturation_lines'][lines]
        index_ht = 'line_ht' if cpt_lines == 0 else 'line_ht_' + str(cpt_lines)
        index_quantity = 'quantity' if cpt_lines == 0 else 'quantity_' + str(cpt_lines)
        index_unit = 'unit_price' if cpt_lines == 0 else 'unit_price_' + str(cpt_lines)
        index_description = 'description' if cpt_lines == 0 else 'description_' + str(cpt_lines)

        args['datas'][index_description] = line['global']['name']
        args['datas'][index_ht] = line['global']['no_rate_amount']
        args['datas'][index_quantity] = line['global']['quantity']
        args['datas'][index_unit] = line['unit_price']['unit_price_ht']
        cpt_lines += 1

    res = insert(args)

    return res


if __name__ == '__main__':
    # with open('/home/nathan/BASIC_Einfach.pdf', 'rb') as f:
    #     _, xml_content = facturx.get_facturx_xml_from_pdf(f.read())
    #     process({'xml_content': xml_content})
    with open('/home/nathan/Facture_FR_EXTENDED.pdf', 'rb') as f:
        _, xml_content = facturx.get_facturx_xml_from_pdf(f.read())
        process({'xml_content': xml_content})
    # with open('/home/nathan/Facture_FR_BASICWL.pdf', 'rb') as f:
    #     _, xml_content = facturx.get_facturx_xml_from_pdf(f.read())
    #     process({'xml_content': xml_content})
    # with open('/home/nathan/EXTENDED_Warenrechnung.pdf', 'rb') as f:
    #     _, xml_content = facturx.get_facturx_xml_from_pdf(f.read())
    #     process({'xml_content': xml_content})
    print('-------------')
