#  (c) Copyright 2015, University of Manchester
#
#  This file is part of the Pyomo Plugin Demo Suite.
#
#  The Pyomo Plugin Demo Suite is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Pyomo Plugin Demo Suite is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Pyomo Plugin Demo Suite.  If not, see <http://www.gnu.org/licenses/>.

#Author: Majed Khadem, Silvia Padula, Khaled Mohamed, Stephen Knox, Julien Harou

from pyomo.environ import *

from pyomo.opt import SolverFactory

# Declaring the model
model = AbstractModel()
# Declaring model indexes using sets
model.nodes = Set()
model.links = Set(within=model.nodes*model.nodes)
model.demand_nodes = Set()
model.non_storage_nodes = Set()
model.storage_nodes = Set()
model.time_step = Set()
model.treatment_hydro_nodes = Set()
model.hydropower=Set()

# Declaring model parameters
model.inflow = Param(model.nodes, model.time_step, default=0)
model.current_time_step = Set()
model.initial_storage = Param(model.storage_nodes, mutable=True)
model.priority = Param(model.demand_nodes, model.time_step, default=0)
model.flow_multiplier = Param(model.links, model.time_step)
model.min_flow = Param(model.links, model.time_step)
model.max_flow = Param(model.links, model.time_step)
model.min_storage = Param(model.nodes, model.time_step)
model.max_storage = Param(model.nodes, model.time_step)
model.demand = Param(model.demand_nodes, model.time_step, default=0)
model.percent_loss = Param(model.treatment_hydro_nodes)
model.net_head = Param(model.hydropower)
model.unit_price = Param()
##======================================== Declaring Variables (X and S)

# Defining the flow lower and upper bound
def flow_capacity_constraint(model, node, node2):
    return model.min_flow[node, node2, model.current_time_step], model.max_flow[node, node2, model.current_time_step]

# Defining the storage lower and upper bound
def storage_capacity_constraint(model, storage_nodes):
    return model.min_storage[storage_nodes, model.current_time_step], model.max_storage[storage_nodes, model.current_time_step]

# Declaring decision variable X

model.flow = Var(model.links, domain=NonNegativeReals, bounds=flow_capacity_constraint) #*1e6 m^3 mon^-1 

# Declaring state variable S
model.storage = Var(model.storage_nodes, bounds=storage_capacity_constraint) #1e6 m^3  

def percent_demand_met_bound(model):
    return 0, 1

model.percent_demand_met = Var(model.demand_nodes, bounds=percent_demand_met_bound) #*%

# Declaring variable alpha
demand_satisfaction_ratio_bound = Constraint(rule=percent_demand_met_bound)

# Defining post process variables
model.received_water = Var(model.nodes) #*1e6 m^3 mon^-1
model.released_water = Var(model.nodes) #*1e6 m^3 mon^-1
model.demand_met = Var(model.demand_nodes) #*%
model.revenue = Var(model.hydropower) #*GBP mon^-1


def get_current_priority(model):
    current_priority = {}
    for node in model.demand_nodes:
        #print link
        current_priority[node] = model.priority[node, model.current_time_step]
    return current_priority  # model.priority [model.current_time_step]

def objective_function(model):
    return summation(get_current_priority(model), model.percent_demand_met)

model.objective_function = Objective(rule=objective_function, sense=maximize)

##======================================== Declaring constraints
# Mass balance for non-storage nodes:

def mass_balance(model, non_storage_nodes):
    # inflow
    term1 = model.inflow[non_storage_nodes, model.current_time_step]
    term2 = sum([model.flow[node_in, non_storage_nodes]*model.flow_multiplier[node_in, non_storage_nodes, model.current_time_step]
                  for node_in in model.nodes if (node_in, non_storage_nodes) in model.links])

    if non_storage_nodes in model.treatment_hydro_nodes:
        term22 = model.percent_loss[non_storage_nodes]
    else:
        term22 = 0

    # outflow

    if non_storage_nodes in model.demand_nodes:
        term3 = model.percent_demand_met[non_storage_nodes] * model.demand[non_storage_nodes, model.current_time_step]
    else:
        term3 = 0

    term4 = sum([model.flow[non_storage_nodes, node_out]
                  for node_out in model.nodes if (non_storage_nodes, node_out) in model.links])

    # inflow - outflow = 0:
    return (term1 + (1-term22) * term2) - (term3 + term4) == 0

model.mass_balance_const = Constraint(model.non_storage_nodes, rule=mass_balance)

# Mass balance for storage nodes:
def storage_mass_balance(model, storage_nodes):
    # inflow
    term1 = model.inflow[storage_nodes, model.current_time_step]
    term2 = sum([model.flow[node_in, storage_nodes]*model.flow_multiplier[node_in, storage_nodes, model.current_time_step]
                  for node_in in model.nodes if (node_in, storage_nodes) in model.links])
    if storage_nodes in model.treatment_hydro_nodes:
        term22 = model.percent_loss[storage_nodes]
    else:
        term22 = 0

    # outflow
    term3 = sum([model.flow[storage_nodes, node_out]
                  for node_out in model.nodes if (storage_nodes, node_out) in model.links])

    # storage
    term4 = model.initial_storage[storage_nodes]
    term5 = model.storage[storage_nodes]
    # inflow - outflow = 0:
    return (term1 + (1-term22) * term2 + term4) - (term3 + term5) == 0

model.storage_mass_balance_const = Constraint(model.storage_nodes, rule=storage_mass_balance)

# Storage capacity constraint for Hydro-power and Treatment nodes


def hydro_treatment_capacity(model, treatment_hydro_nodes):
    return 0 <= sum([model.flow[node_in, treatment_hydro_nodes]*model.flow_multiplier[node_in, treatment_hydro_nodes, model.current_time_step]
                  for node_in in model.nodes if (node_in, treatment_hydro_nodes) in model.links]) <= model.max_storage[treatment_hydro_nodes, model.current_time_step]

model.hydro_treatment_capacity_constraint = Constraint(model.treatment_hydro_nodes, rule=hydro_treatment_capacity)


def released(instance):
    for i in instance.nodes:
        instance.released_water[i]=sum([instance.flow[i, node_out].value for node_out in instance.nodes if (i, node_out) in instance.links])


def received(instance):
    for i in instance.nodes:
        instance.received_water[i].value=sum([instance.flow_multiplier[node_in, i, instance.current_time_step]*instance.flow[node_in, i].value for node_in in instance.nodes if (node_in, i) in instance.links])


def demand_met(instance):
    for i in instance.demand_nodes:
        instance.demand_met[i].value= instance.received_water[i].value - instance.released_water[i].value


def revenue(instance):
    for i in instance.hydropower:
        instance.revenue[i].value=(1-instance.percent_loss[i])*instance.received_water[i].value*9.81*24*0.3858*instance.net_head[i]*instance.unit_price


def get_storage(instance):
    storage_levels={}
    for i in instance.storage_nodes:
        storage_levels[i]=instance.storage[i].value
    return storage_levels



def set_initial_storage(instance, storage_levels):
    for i in instance.storage_nodes:
        instance.initial_storage[i].value =storage_levels[i]


def set_post_process_variables(instance):
    released(instance)
    received(instance)
    demand_met(instance)
    revenue(instance)


def run_model(datafile):
    print "==== Running the model ===="
    opt = SolverFactory("cplex")
    list = []
    list_ = []
    model.current_time_step.add(1)
    instance = model.create_instance(datafile)
    ## determine the time steps
    for comp in instance.component_objects():
        if str(comp) == "time_step":
            parmobject = getattr(instance, str(comp))
            for vv in parmobject.value:
                list_.append(vv)
    storage = {}
    insts = []

    for vv in list_:
        model.current_time_step.clear()
        model.current_time_step.add(vv)
        print "Running for time step: ", vv

        instance = model.create_instance(datafile)
        # update initial storage value from previous storage
        if len(storage) > 0:
            set_initial_storage(instance, storage)
            instance.preprocess()

        res=opt.solve(instance)  
        instance.solutions.load_from(res)
        set_post_process_variables(instance)
        insts.append(instance)
        storage=get_storage(instance)
        list.append(res)
        print "-------------------------"
    count=1
    for res in list:
        print " ========= Time step:  %s =========="%count
        print res
        count+=1
    count=1

    for inst in insts:
        print " ========= Time step:  %s =========="%count
        display_variables(inst)
        count+=1
    return list, insts


def display_variables(instance):
    for var in instance.component_objects(Var):
        s_var = getattr(instance, str(var))
        print "=================="
        print "Variable: %s"%s_var
        print "=================="
        for vv in s_var:
            if vv is None:
                print s_var," : ", s_var.value
                continue
            if type(vv) is str:
                name = ''.join(map(str,vv))
                print name ,": ",(s_var[vv].value)
            elif len(vv) == 2:
                name = "[" + ', '.join(map(str,vv)) + "]"
                print name ,": ",(s_var[vv].value)

##========================
# running the model in a loop for each time step
if __name__ == '__main__':
    run_model("input.dat")
