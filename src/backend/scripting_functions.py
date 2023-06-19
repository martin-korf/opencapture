# This file is part of Open-Capture.
from flask_babel import gettext

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

# @dev : Nathan Cheval <nathan.cheval@edissyum.com>

from src.backend.main import launch


def send_to_workflow(args):
    workflow = args['database'].select({
        'select': ['input'],
        'table': ['workflows'],
        'where': ['workflow_id = %s'],
        'data': [args['workflow_id']]
    })

    if not workflow:
        args['log'].error(gettext('WORFKLOW_NOT_FOUND'))
        return False

    launch({
        'ip': args['ip'],
        'log': args['log'],
        'file': args['file'],
        'user_info': args['user_info'],
        'custom_id': args['custom_id'],
        'workflow_id': args['workflow_id'],
        'task_id_monitor': args['log'].task_id_monitor
    })