from webcolors import name_to_hex
import sys
import requests
import json

import logging

from .utils import hydra_timeseries, eval_data

log = logging.getLogger(__name__)

def get_coords(nodes):
    coords = {}
    for n in nodes:
        coords[n.id] = [float(n.x), float(n.y)] 
    return coords

class connection(object):

    def __init__(self, url=None, session_id=None,
                 user_id=None, app_name=None,
                 project_id=None, project_name=None,
                 network_id=None, network_name=None,
                 template_id=None, template_name=None,
                 ttypes=None):
        self.url = url
        self.app_name = app_name
        self.session_id = session_id
        self.user_id = user_id

    def call(self, func, args):
        log.info("Calling: %s" % (func))
        headers = {'Content-Type': 'application/json',
                   'sessionid': self.session_id,
                   'appname': self.app_name}
        
        data = json.dumps({func: args})

        response = requests.post(self.url, data=data, headers=headers)
        if not response.ok:
            try:
                fc, fs = response['faultcode'], response['faultstring']
                log.debug('Something went wrong. Check faultcode and faultstring.')
                resp = json.loads(response.content.decode("utf-8"))
                err = "faultcode: %s, faultstring: %s" % (fc, fs)
            except:                
                log.debug('Something went wrong. Check command sent.')
                log.debug("URL: %s"%self.url)
                log.debug("Function called: %s" % json.dumps(func))             

                if response.content != '':
                    err = response.content
                else:
                    err = "Something went wrong. An unknown server has occurred."

            # need to figure out how to raise errors
        
        log.info('Finished communicating with Hydra Platform.')

        resp = json.loads(response.content.decode("utf-8"), object_hook=JSONObject)
        return resp

    def login(self, username=None, password=None):
        if username is None:
            err = 'Error. Username not provided.'
            # raise error
        response = self.call('login', {'username': username, 'password': password})
        self.session_id = response.sessionid
        self.user_id = response.userid
        log.info("Session ID: %s", self.session_id)

    # specific methods
    def get_user_by_name(self, username=None):
        if username is None:
            err = 'Error. Username not provided.'
        resp = self.call('get_user_by_name', {'username': username})        
        return resp  
    
    def get_project_by_name(self, project_name=None):
        if project_name is None:
            err = 'Error. Project name not provided'
        resp = self.call('get_project_by_name', {'project_name':project_name})  
        return resp
    
    def get_network_by_name(self, project_id=None, network_name=None):
        if project_id is None:
            err = 'Error. Project ID not provided'
        if network_name is None:
            err = 'Error. Network name not provided'
        resp = self.call('get_network_by_name',
                         {'project_id':project_id, 'network_name':network_name})
        return resp
    
    def add_project(self, project_data=None):
        return self.call('add_project', project_data)
    
    def get_network(self, network_id=None, include_data='N'):
        return self.call('get_network', {'network_id':network_id,
                                         include_data: include_data})
    
    def get_template(self, template_id=None):
        return self.call('get_template', {'template_id':template_id})
    
    def get_node(self, node_id=None):
        return self.call('get_node',{'node_id':node_id})
    
    def make_geojson_from_node(self, node=None):
        type_id = [t.id for t in node.types \
                   if t.template_id==self.template_id][0]
        ttype = self.ttypes[type_id]
        gj = {'type':'Feature',
              'geometry':{'type':'Point',
                          'coordinates':[node.x, node.y]},
              'properties':{'name':node.name,
                            'id':node.id,
                            'description':node.description,
                            'template_type_name':ttype.name,
                            'template_type_id':ttype.id,
                            'image':ttype.layout.image,
                            'template_name':self.template_name}}
        return gj

    def make_geojson_from_link(self, link=None):
        
        coords = get_coords(self.network.nodes)
        
        type_id = [t.id for t in link.types \
                   if t.template_id==self.template_id][0]
        ttype = self.ttypes[type_id]

        n1_id = link['node_1_id']
        n2_id = link['node_2_id']
        
        # for dash arrays, see:
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/stroke-dasharray
        symbol = ttype.layout.symbol
        if symbol=='solid':
            dashArray = '1,0'
        elif symbol=='dashed':
            dashArray = '5,5'
            
        gj = {'type':'Feature',
             'geometry':{ 'type': 'LineString',
                          'coordinates': [coords[n1_id],coords[n2_id]] },
             'properties':{'name':link.name,
                           'id':link.id,
                           'description':link.description,
                           'template_type_name':ttype.name,
                           'template_type_id':ttype.id,
                           'image':ttype.layout.image,
                           'template_name':self.template_name,
                           'color': name_to_hex(ttype.layout.colour),
                           'weight': ttype.layout.line_weight,
                           'opacity': 0.7,
                           'dashArray': dashArray,
                           'lineJoin': 'round'
                           }
             }
        return gj
        
    # make geojson features
    def make_geojson_features(self):
        
        nodes_gj = \
            [self.make_geojson_from_node(node) for node in self.network.nodes]
        
        links_gj = \
            [self.make_geojson_from_link(link) \
             for link in self.network.links]

        features = nodes_gj + links_gj
    
        return features
    
    # convert geoJson node to Hydra node
    def make_node_from_geojson(self, gj=None):
        x, y = gj['geometry']['coordinates']
        template_type_name = gj['properties']['template_type_name']
        template_type_id = int(gj['properties']['template_type_id'])
        
        typesummary = dict(
            name = template_type_name,
            id = template_type_id,
            template_name = self.template_name,
            template_id = self.template_id
        )
        node = dict(
            id = -1,
            name = gj['properties']['name'],
            description = gj['properties']['description'],
            x = str(x),
            y = str(y),
            types = [typesummary]
        )
        return node
    
    def make_links_from_geojson(self, gj=None):
        
        coords = get_coords(self.network.nodes)
        
        d = 3 # rounding decimal points to match link coords with nodes.
        nlookup = {(round(x,d), round(y,d)): k for k, [x, y] in coords.items()}
        xys = []
        for [x,y] in gj['geometry']['coordinates']:
            xy = (round(x,d), round(y,d))
            xys.append(xy)
        
        lname = gj['properties']['name'] # link name
        desc = gj['properties']['description']
        template_type_name = gj['properties']['template_type_name']
        template_type_id = int(gj['properties']['template_type_id'])
        
        typesummary = dict(
            name = template_type_name,
            id = template_type_id,
            template_name = self.template_name,
            template_id = self.template_id
        )

        links = []
        nsegments = len(xys) - 1        
        for i in range(nsegments):
            
            node_1_id = nlookup[xys[i]]
            node_2_id = nlookup[xys[i+1]]

            link = dict(
                node_1_id = node_1_id,
                node_2_id = node_2_id,
                types = [typesummary]
            )
            if len(lname) and nsegments == 1:
                link['name'] = lname
                link['description'] = desc
            elif len(lname) and nsegments > 1:
                link['name'] = '{}_{:02}'.format(lname, i+1)
                link['description'] = '{} (Segment {})'.format(desc, i+1)
            else:
                n1_name = self.get_node(node_1_id).name
                n2_name = self.get_node(node_2_id).name
                link['name'] = '{}_{}'.format(n1_name, n2_name)
                link['description'] = '{} from {} to {}' \
                    .format(template_type_name, n1_name, n2_name)
                
        links.append(link)
        return links  
    
class JSONObject(dict):
    def __init__(self, obj_dict):
        for k, v in obj_dict.items():
            self[k] = v
            setattr(self, k, v)
            
def make_connection(session,
                    include_network=True,
                    include_template=True):
    
    conn = connection(url=session['url'],
                      session_id=session['session_id'])
    
    for i in ['user_id', 'appname',
              'project_id', 'project_name',
              'network_id', 'network_name',
              'template_id', 'template_name']:
        exec("conn.%s = session['%s']" % (i,i))
    
    if include_network:
        conn.network = conn.get_network(network_id = session['network_id'],
                                        include_data = 'N')
    
    if include_template:
        conn.template = conn.get_template(template_id = session['template_id'])
    
        ttypes = {}
        for tt in conn.template.types:
            ttypes[tt.id] = tt
        conn.ttypes = ttypes    
    
    return conn

def save_data(conn, old_data_type, cur_data_type, res_attr, res_attr_data, new_value,
              metadata, scen_id):

    if cur_data_type == 'function':
        new_data_type = 'timeseries'
        metadata['function'] = new_value
        new_value = json.dumps(hydra_timeseries(eval_data('generic', "''")))
    else:
        new_data_type = cur_data_type
        metadata['function'] = ''

    # has the data type changed?
    if new_data_type != old_data_type:
        # 1. copy old typeattr:
        old_typeattr = {'attr_id': res_attr['attr_id'],
                        'type_id': res_attr['type_id']}
        # 2. delete the old typeattr
        result = conn.call('delete_typeattr', {'typeattr': old_typeattr})
        # 3. update the old typeattr with the new data type
        new_typeattr = old_typeattr
        new_typeattr['attr_is_var'] = 'N'
        new_typeattr['data_type'] = new_data_type
        new_typeattr['unit'] = res_attr['unit']
        # 3. add the new typeattr
        result = conn.call('add_typeattr', {'typeattr': new_typeattr})
                
    if res_attr_data is None: # add a new dataset
        
        dataset = dict(
            id=None,
            name = res_attr['res_attr_name'],
            unit = res_attr['unit'],
            dimension = res_attr['dimension'],
            type = new_data_type,
            value = new_value,
            metadata = json.dumps(metadata)
        )
        
        args = {'scenario_id': scen_id,
                'resource_attr_id': res_attr['res_attr_id'],
                'dataset': dataset}
        result = conn.call('add_data_to_attribute', args)  
            
    else: # just update the existing dataset
        dataset = res_attr_data['value']
        dataset['type'] = new_data_type
        dataset['value'] = new_value
        dataset['metadata'] = json.dumps(metadata)
        
        result = conn.call('update_dataset', {'dataset': dataset})
        
    if 'faultcode' in result.keys():
        returncode = -1
    else:
        returncode = 1
    return returncode