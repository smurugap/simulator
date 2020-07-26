from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from agent.fabric import Fabric
from agent.sflow import sFlow
from agent.netconf import Netconf
from common.exceptions import InvalidUsage

app = Flask(__name__)
api = Api(app, version='1.0', title='Simulator Agent API',
          description='Simulator Agent API')

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

# Register Fabric wide operations api
ns_fabric = api.namespace('fabric', description='Fabric wide Apis')
fabric_put_schema = {
    'address_pool': fields.String(required=True,
        description='List of address pools - eg: [("10.1.1.10", "10.1.1.20"),'
                    ' ("10.1.1.30", "10.1.1.40")]'),
    'n_leafs': fields.Integer(required=True,
        description='No of leafs in the fabric'),
    'n_spines': fields.Integer(required=True,
        description='No of spines in the fabric'),
    'n_border_leafs': fields.Integer(
        description='No of border leafs in the fabric'),
    'n_pifs': fields.Integer(
        description='No of physical interfaces in each Leaf - eg: 48'),
    'collector': fields.String(
        description='Address of the sflow collector if action is start')
}
fabric_post_schema = dict(fabric_put_schema)
fabric_post_schema.update({
    'interface': fields.String(required=True,
        description='Physical interface on the host - eg: enp129s0f1'),
    'subnet': fields.String(required=True,
        description='CIDR to assign to simulator instances - eg: 10.1.1.0/24'),
    'gateway': fields.String(required=True,
        description='Gateway address for the simulator instances - eg: 10.1.1.254')})
fabric_put_model = api.model('fabric_put_model', fabric_put_schema)
fabric_post_model = api.model('fabric_post_model', fabric_post_schema)

@ns_fabric.route("/<string:fabric_name>")
class FlaskFabric(Resource):
    def get(self, fabric_name):
        return Fabric.get(fabric_name)

    @ns_fabric.expect(fabric_post_model)
    def post(self, fabric_name):
        data = request.get_json(force=True)
        return Fabric().post(fabric_name, **data)

    @ns_fabric.expect(fabric_put_model)
    def put(self, fabric_name):
        data = request.get_json(force=True)
        return Fabric().put(fabric_name, **data)

    def delete(self, fabric_name):
        return Fabric.delete(fabric_name)

@ns_fabric.route("/")
class FlaskFabricList(Resource):
    def get(self):
        return Fabric.get()

# Register sFlow engine apis
ns_sflow = api.namespace('sflow', description='sFlow start/stop actions')
sflow_schema = {
    'action': fields.String(required=True, description='start or stop sflows'),
    'direction': fields.String(description='ingress or egress direction for sflow collection'),
    'bms_per_router': fields.String(description='No of BMS servers per Device (floor and not ceil)'),
    'n_flows': fields.Integer(description='No of sampled flows if action is "start"')
}
sflow_model = api.model('sflow_model', sflow_schema)
@ns_sflow.route("/<string:fabric_name>")
class FlaskSFlow(Resource):
    @ns_sflow.expect(sflow_model)
    def post(self, fabric_name):
        data = request.get_json(force=True)
        sFlow().post(fabric_name, **data)

# Register netconf engine apis
ns_netconf = api.namespace('netconf', description='Send events to netconf engine')
netconf_schema = {
    'kv_pairs': fields.List(fields.Nested(api.model('kv_model',
        {'key': fields.String, 'value': fields.String}))),
    'template': fields.Nested(api.model('template_model',
        {'rpc_name': fields.String, 'content': fields.String})),
    'devices': fields.List(fields.String, description='List of devices')
}
netconf_model = api.model('netconf_model', netconf_schema)
@ns_netconf.route("/<string:fabric_name>")
class FlaskNetconf(Resource):
    def get(self, fabric_name):
        devices = request.args.get('devices')
        raw = request.args.get('raw')
        if devices:
            devices = devices.split(',')
        return Netconf().get(fabric_name, devices, raw)

    @ns_netconf.expect(netconf_model)
    def post(self, fabric_name):
        data = request.get_json(force=True)
        Netconf().post(fabric_name, **data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8989)
