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
import os
import sys
import time
import tempfile
from kuyruk import Kuyruk
from kuyruk_manager import Manager
from .functions import recursive_delete
from .import_process import OCForInvoices_process
from .import_classes import _Database, _PyTesseract, _Locale, _Xml, _Files, _Log, _Config, invoice_classification, \
    _WebServices, _SeparatorQR, _Splitter

OCforInvoices_worker = Kuyruk()

OCforInvoices_worker.config.MANAGER_HOST = "127.0.0.1"
OCforInvoices_worker.config.MANAGER_PORT = 16501
OCforInvoices_worker.config.MANAGER_HTTP_PORT = 16500

m = Manager(OCforInvoices_worker)


def create_classes(config_name):
    config = _Config(config_name.cfg['PROFILE']['cfgpath'] + '/config_' + config_name.cfg['PROFILE']['id'] + '.ini')
    locale = _Locale(config)
    log = _Log(config.cfg['GLOBAL']['logfile'])
    ocr = _PyTesseract(locale.localeOCR, log, config)
    db_user = config.cfg['DATABASE']['postgresuser']
    db_pwd = config.cfg['DATABASE']['postgrespassword']
    db_name = config.cfg['DATABASE']['postgresdatabase']
    db_host = config.cfg['DATABASE']['postgreshost']
    db_port = config.cfg['DATABASE']['postgresport']
    database = _Database(log, db_name, db_user, db_pwd, db_host, db_port)
    xml = _Xml(config, database)
    separator_qr = _SeparatorQR(log, config)
    splitter = _Splitter(config, database, locale, separator_qr)
    return config, locale, log, ocr, database, xml, splitter, separator_qr


def check_file(files, path, config, log):
    if not files.check_file_integrity(path, config):
        log.error('The integrity of file could\'nt be verified : ' + str(path))
        return False


def timer(start_time, end_time):
    hours, rem = divmod(end_time - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)


def get_typo(config, path, log):
    invoice_classification.MODEL_PATH = config.cfg['AI-CLASSIFICATION']['modelpath']
    invoice_classification.PREDICT_IMAGES_PATH = config.cfg['AI-CLASSIFICATION']['trainimagepath']
    invoice_classification.TRAIN_IMAGES_PATH = config.cfg['AI-CLASSIFICATION']['predictimagepath']
    typo, confidence = invoice_classification.predict_typo(path)

    if typo:
        if confidence >= config.cfg['AI-CLASSIFICATION']['confidencemin']:
            log.info('Typology n°' + typo + ' found using AI with a confidence of ' + confidence + '%')
            return typo
        else:
            log.info('Typology can\'t be found using AI, the confidence is too low : Typo n°' + typo + ', confidence : ' + confidence + '%')
            return False
    else:
        log.info('Typology can\'t be found using AI')
        return False


# If needed just run "kuyruk --app src.backend.main.OCforInvoices_worker manager"
# to have web dashboard of current running worker
@OCforInvoices_worker.task(queue='invoices')
def launch(args):
    start = time.time()

    # Init all the necessary classes
    config_name = _Config(args['config'])
    config_file = config_name.cfg['PROFILE']['cfgpath'] + '/config_' + config_name.cfg['PROFILE']['id'] + '.ini'

    if not os.path.exists(config_file):
        sys.exit('config file couldn\'t be found')

    config, locale, log, ocr, database, xml, splitter, separator_qr = create_classes(config_name)
    tmp_folder = tempfile.mkdtemp(dir=config.cfg['GLOBAL']['tmppath'])
    filename = tempfile.NamedTemporaryFile(dir=tmp_folder).name
    files = _Files(
        filename,
        int(config.cfg['GLOBAL']['resolution']),
        int(config.cfg['GLOBAL']['compressionquality']),
        xml,
        log,
        config.cfg['GLOBAL']['convertpdftotiff'],
        locale,
        config
    )

    if config.cfg['GED']['enabled'] != 'False':
        webservices = _WebServices(
            config.cfg['GED']['host'],
            config.cfg['GED']['user'],
            config.cfg['GED']['password'],
            log,
            config
        )
    else:
        webservices = False

    # Connect to database
    database.connect()

    # Start process
    if 'path' in args and args['path'] is not None:
        path = args['path']
        for file in os.listdir(path):
            if check_file(files, path + file, config, log) is not False and not os.path.isfile(path + file + '.lock'):
                os.mknod(path + file + '.lock')
                log.info('Lock file created : ' + path + file + '.lock')

                # Find file in the wanted folder (default or exported pdf after qrcode separation)
                typo = ''
                if config.cfg['AI-CLASSIFICATION']['enabled'] == 'True':
                    typo = get_typo(config, path + file, log)

                OCForInvoices_process.process(path + file, log, config, files, ocr, locale, database, webservices, typo)

                try:
                    os.remove(path + file + '.lock')
                    log.info('Lock file removed : ' + path + file + '.lock')
                except FileNotFoundError:
                    pass

    elif 'file' in args and args['file'] is not None:
        path = args['file']
        typo = ''
        if config.cfg['AI-CLASSIFICATION']['enabled'] == 'True':
            typo = get_typo(config, path, log)

        if check_file(files, path, config, log) is not False:
            # Process the file and send it to Maarch
            OCForInvoices_process.process(path, log, config, files, ocr, locale, database, webservices, typo)

    # Empty the tmp dir to avoid residual file
    recursive_delete(tmp_folder, log)

    # Close database
    database.conn.close()

    end = time.time()
    log.info('Process end after ' + timer(start, end) + '')
