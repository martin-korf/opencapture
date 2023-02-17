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

from flask import request, g as current_context
from src.backend.functions import retrieve_custom_from_url
from src.backend.main import create_classes_from_custom_id


def get_monitoring(args):
    if 'database' in current_context:
        database = current_context.database
    else:
        custom_id = retrieve_custom_from_url(request)
        _vars = create_classes_from_custom_id(custom_id)
        database = _vars[0]
    error = None
    _monitoring = database.select({
        'select': ['*'] if 'select' not in args else args['select'],
        'table': ['monitoring'],
        'where': args['where'] if 'where' in args else [],
        'data': args['data'] if 'data' in args else [],
        'order_by': args['order_by'] if 'order_by' in args else [],
        'limit': str(args['limit']) if 'limit' in args else 'ALL',
        'offset': str(args['offset']) if 'offset' in args else 0,
    })
    return _monitoring, error
