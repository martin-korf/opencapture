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

import json
from flask_babel import gettext
from flask import Blueprint, request, make_response, jsonify
from src.backend.import_controllers import auth, workflow, privileges

bp = Blueprint('workflow', __name__, url_prefix='/ws/')


@bp.route('workflow/<string:module>/verifyInputFolder', methods=['POST'])
@auth.token_required
def verify_input_folder(module):
    list_priv = ['settings', 'add_workflow | update_workflow'] if module == 'verifier' else ['add_workflow_splitter | update_workflow_splitter']
    if not privileges.has_privileges(request.environ['user_id'], list_priv):
        return jsonify({'errors': gettext('UNAUTHORIZED_ROUTE'),
                        'message': f'/workflow/{module}/verifyInputFolder'}), 403

    data = json.loads(request.data)
    res = workflow.verify_input_folder(data)
    return make_response(jsonify(res[0])), res[1]


@bp.route('workflows/<string:module>/list', methods=['GET'])
@auth.token_required
def get_workflows(module):
    list_priv = ['settings', 'workflows_list'] if module == 'verifier' else ['settings', 'workflows_list_splitter']
    if not privileges.has_privileges(request.environ['user_id'], list_priv):
        return jsonify({'errors': gettext('UNAUTHORIZED_ROUTE'), 'message': f'/workflows/{module}/list'}), 403

    args = dict(request.args)
    args['module'] = module
    _workflows = workflow.get_workflows(args)
    return make_response(jsonify(_workflows[0])), _workflows[1]


@bp.route('workflows/<string:module>/getById/<int:workflow_id>', methods=['GET'])
@auth.token_required
def get_form_by_id(workflow_id, module):
    list_priv = ['settings', 'update_workflow'] if module == 'verifier' else ['settings', 'update_workflow_splitter']
    if not privileges.has_privileges(request.environ['user_id'], list_priv):
        return jsonify({'errors': gettext('UNAUTHORIZED_ROUTE'),
                        'message': f'/workflow/{module}/getById/{workflow_id}'}), 403

    _form = workflow.get_workflow_by_id(workflow_id)
    return make_response(jsonify(_form[0])), _form[1]


@bp.route('workflows/<string:module>/duplicate/<int:workflow_id>', methods=['POST'])
@auth.token_required
def duplicate_workflow(module, workflow_id):
    list_priv = ['settings', 'update_workflow'] if module == 'verifier' else ['settings', 'update_workflow_splitter']
    if not privileges.has_privileges(request.environ['user_id'], list_priv):
        return jsonify({'errors': gettext('UNAUTHORIZED_ROUTE'),
                        'message': f'/workflows/{module}/duplicate/{workflow_id}'}), 403

    res = workflow.duplicate_workflow(workflow_id)
    return make_response(jsonify(res[0])), res[1]


@bp.route('workflows/<string:module>/delete/<int:workflow_id>', methods=['DELETE'])
@auth.token_required
def delete_workflow(module, workflow_id):
    list_priv = ['settings', 'update_workflow'] if module == 'verifier' else ['settings', 'update_workflow_splitter']
    if not privileges.has_privileges(request.environ['user_id'], list_priv):
        return jsonify({'errors': gettext('UNAUTHORIZED_ROUTE'),
                        'message': f'/workflows/{module}/delete/{workflow_id}'}), 403

    res = workflow.delete_workflow(workflow_id)
    return make_response(jsonify(res[0])), res[1]
