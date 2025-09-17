import pulp
from pulp import LpProblem, LpMaximize, LpStatus, PULP_CBC_CMD


def stringify_keys(d):
    return {str(k): v for k, v in d.items()}

def calculation(parameters):
    """
    Calculate the optimal activation of flexible loads using linear programming to maximize cost savings while
    meeting usage constraints.

    Parameters:
        parameters (dict): A dictionary containing various input parameters for the optimization problem,
                           including electricity prices, energy flexibility details, measure costs

    Returns:
        tuple: 
               - calculation outputs 
               - solution status
    """

    electricity_price = parameters["electricity_price"]
    optimization_duration_intervals_num = parameters["optimization_duration_intervals_num"]
    time_interval_duration_hours = parameters["time_interval_duration_hours"]
    start_cost = parameters["start_cost"]
    usageNumber_max = parameters["usageNumber_max"]
    usageNumber_min = parameters["usageNumber_min"]
    power_for_measure = parameters["power_for_measure"]
    time_length_of_measure = parameters["time_length_of_measure"]
    validity_in_time_format = parameters["validity_in_time_format"]
    regeneration_time = parameters["regeneration_time"]
    time_set = parameters["time_set"]
    measure_set = parameters["measure_set"]
    max_lenght_of_measure_among_all_efdms = parameters["max_lenght_of_measure_among_all_efdms"]
    flexibilities_set = parameters["flexibilities_set"]
    measure_num_of_each_machine = parameters["measure_num_of_each_machine"]

    # Problem definition
    prob = LpProblem("Flex", LpMaximize)

    # Variables definition
    x_vars = pulp.LpVariable.dicts("x_var", (flexibilities_set, time_set), cat='Binary')
    y_vars = pulp.LpVariable.dicts("y_var", (flexibilities_set, measure_set, time_set), cat='Binary')
    z_vars_end = pulp.LpVariable.dicts("z_vars_end", (flexibilities_set, measure_set, time_set), cat='Binary')
    cost_vars = pulp.LpVariable.dicts(
        "cost_vars", (flexibilities_set, measure_set), cat="Continuous")

    # New variable for power consumption
    measure_power_consumption = pulp.LpVariable.dicts(
        "measure_power_consumption", (flexibilities_set, measure_set), cat="Continuous")
    
    # Variable for activation cost
    cost_act_vars = pulp.LpVariable.dicts(
        "cost_act_vars", (flexibilities_set, measure_set), cat="Continuous")
    
    # Objective function
    prob += (pulp.lpSum(
        time_interval_duration_hours * y_vars[f][m][t] * power_for_measure[f, m, i] * -electricity_price[t + i - 1] / 1000
        for f in flexibilities_set 
        for m in measure_set 
        for t in time_set 
        for i in max_lenght_of_measure_among_all_efdms 
        if (t + i - 1) < optimization_duration_intervals_num + 1)
             - pulp.lpSum(y_vars[f][m][t] * start_cost[f, m] 
                          for f in flexibilities_set 
                          for m in measure_set 
                          for t in time_set), "Total saving",)
    
    # Usage number constraints 
    for f in flexibilities_set:
        prob += pulp.lpSum(x_vars[f][t] for t in time_set) >= usageNumber_min[f - 1]
    for f in flexibilities_set:
        prob += pulp.lpSum(x_vars[f][t] for t in time_set) <= usageNumber_max[
            f - 1] 
        
    # Relationship between x and y variables
    for t in time_set:
        for f in flexibilities_set:
            prob += x_vars[f][t] == pulp.lpSum(y_vars[f][m][t] for m in measure_set)

    # Constraints to ensure that only valid measures can be activated
    for t in time_set:
        for f in range(len(measure_num_of_each_machine)):
            prob += 0 == pulp.lpSum(y_vars[f + 1][m][t] for m in
                                    range(measure_num_of_each_machine[f] + 1, max(measure_num_of_each_machine) + 1))
            
    # Constraints to ensure that only valid measures can be activated
    for f in flexibilities_set:
        for t in time_set:
            for m in measure_set:
                prob += y_vars[f][m][t] <= validity_in_time_format[f - 1][t - 1]

    # Constraints to link y and z variables
    for f in flexibilities_set:
        for t in time_set:
            for m in measure_set:
                if t + time_length_of_measure[f, m] <= optimization_duration_intervals_num:
                                                            prob += y_vars[f][m][t] == z_vars_end[f][m][t + time_length_of_measure[f, m]]

    # Constraints to ensure measures fit within the optimization horizon and respect regeneration times
    for f in flexibilities_set:
        for t in time_set:
            for m in measure_set:
                prob += y_vars[f][m][t] * (t + time_length_of_measure[f, m] + regeneration_time[f, m]) <= optimization_duration_intervals_num

    # Regeneration time constraints
    for f in flexibilities_set:
        for t in time_set:
            for m in measure_set:
                if regeneration_time[f, m] > 0:
                    prob += pulp.lpSum(
                        y_vars[f][m][t + h + time_length_of_measure[f, m] - 1] 
                        for h in range(1, regeneration_time[f, m] + 1) 
                        if (t + h + time_length_of_measure[f, m] - 1) <= 
                                            optimization_duration_intervals_num) <= regeneration_time[f, m] * (1 - y_vars[f][m][t])
                    
    # Prevent overlapping measures on the same flexibility
    for f in flexibilities_set:
        for m in measure_set:
            for t in time_set:
                if time_length_of_measure[f, m] >= 2:
                    prob += pulp.lpSum(x_vars[f][t + h - 1] for h in range(2, time_length_of_measure[f, m] + 1 + regeneration_time[f, m]) 
                                       if (t + h - 1) <= optimization_duration_intervals_num) <= (
                                                             1 - y_vars[f][m][t]) * (time_length_of_measure[f, m] + regeneration_time[f, m] - 1)  
                    
    # Cost calculation constraints
    for f in flexibilities_set:
        for m in measure_set:
            prob += cost_vars[f][m] == pulp.lpSum(
                                                y_vars[f][m][t] * power_for_measure[f, m, i] * electricity_price[t + i - 1] 
                                                for t in time_set 
                                                for i in max_lenght_of_measure_among_all_efdms 
                                                if (t + i - 1) < optimization_duration_intervals_num + 1)
    # Activation cost calculation constraints
    for f in flexibilities_set:
        for m in measure_set:
            prob += cost_act_vars[f][m] == pulp.lpSum(
                                                y_vars[f][m][t] * start_cost[f, m] for t in time_set)

    # Dependency constraints

    list_of_dependencies_x2_implies_starts_from_a_to_b_step_start_x1 = parameters[
        "list_of_dependencies_x2_implies_starts_from_a_to_b_step_start_x1"]  # [(x1,x2,a,b)]

    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_implies_starts_from_a_to_b_step_start_x1:
            prob += x_vars[a1][t] <= pulp.lpSum(x_vars[a2][t + a] 
                                                for a in range(a3, a4 + 1) 
                                                if 1 <= t + a <= optimization_duration_intervals_num)  

    list_of_dependencies_x2_implies_starts_from_a_to_b_step_ends_x1 = parameters[
        "list_of_dependencies_x2_implies_starts_from_a_to_b_step_ends_x1"]  # [(x1,x2,a,b)]

    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_implies_starts_from_a_to_b_step_ends_x1:
            prob += x_vars[a1][t] <= pulp.lpSum(z_vars_end[a2][m][t + a] 
                                                for m in measure_set 
                                                for a in range(a3, a4 + 1) 
                                                if 1 <= t + a <= optimization_duration_intervals_num)

    list_of_dependencies_x2_implies_ends_from_a_to_b_step_start_x1 = parameters[
        "list_of_dependencies_x2_implies_ends_from_a_to_b_step_start_x1"]  # [(x1,x2,a,b)]

    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_implies_ends_from_a_to_b_step_start_x1:
            prob += pulp.lpSum(z_vars_end[a1][m][t] for m in measure_set) <= pulp.lpSum(
                                                                                x_vars[a2][t + a] 
                                                                                for a in range(a3, a4 + 1) 
                                                                                if 1 <= t + a <= optimization_duration_intervals_num)

    list_of_dependencies_x2_implies_ends_from_a_to_b_step_ends_x1 = parameters[
        "list_of_dependencies_x2_implies_ends_from_a_to_b_step_ends_x1"]  # [(x1,x2,a,b)]

    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_implies_ends_from_a_to_b_step_ends_x1:
            prob += pulp.lpSum(
                            z_vars_end[a1][m][t] for m in measure_set) <= pulp.lpSum(
                                                                                z_vars_end[a2][m][t + a] 
                                                                                for m in measure_set 
                                                                                for a in range(a3, a4 + 1) 
                                                                                if 1 <= t + a <= optimization_duration_intervals_num)

    list_of_dependencies_x2_excludes_starts_from_a_to_b_step_start_x1 = parameters[
        "list_of_dependencies_x2_excludes_starts_from_a_to_b_step_start_x1"]
    
    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_excludes_starts_from_a_to_b_step_start_x1:
            prob += pulp.lpSum(
                            x_vars[a2][t + a] 
                            for a in range(a3, a4 + 1) 
                            if 1 <= t + a <= optimization_duration_intervals_num) <= (1 - x_vars[a1][t]) * (a4 - a3 + 1)

    list_of_dependencies_x2_excludes_starts_from_a_to_b_step_ends_x1 = parameters[
        "list_of_dependencies_x2_excludes_starts_from_a_to_b_step_ends_x1"]
    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_excludes_starts_from_a_to_b_step_ends_x1:
            prob += pulp.lpSum(
                            z_vars_end[a2][m][t + a] 
                            for m in measure_set 
                            for a in range(a3, a4 + 1) 
                            if 1 <= t + a <= optimization_duration_intervals_num) <= (1 - x_vars[a1][t]) * (a4 - a3 + 1)

    list_of_dependencies_x2_excludes_ends_from_a_to_b_step_start_x1 = parameters[
        "list_of_dependencies_x2_excludes_ends_from_a_to_b_step_start_x1"]
    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_excludes_ends_from_a_to_b_step_start_x1:
            prob += pulp.lpSum(
                            x_vars[a2][t + a] 
                            for a in range(a3, a4 + 1) 
                            if 1 <= t + a <= 
                            optimization_duration_intervals_num) <= (
                                                                     1 - pulp.lpSum(z_vars_end[a1][m][t] for m in measure_set)) * (a4 - a3 + 1)

    list_of_dependencies_x2_excludes_ends_from_a_to_b_step_ends_x1 = parameters[
        "list_of_dependencies_x2_excludes_ends_from_a_to_b_step_ends_x1"]
    
    for t in time_set:
        for a1, a2, a3, a4 in list_of_dependencies_x2_excludes_ends_from_a_to_b_step_ends_x1:
            prob += pulp.lpSum(z_vars_end[a2][m][t] 
                               for m in measure_set 
                               for a in range(a3, a4 + 1) 
                               if 1 <= t + a <= 
                               optimization_duration_intervals_num) <= (
                                                                       1 - pulp.lpSum(z_vars_end[a1][m][t] for m in measure_set)) * (a4 - a3 + 1)

    for f in flexibilities_set:
        for m in measure_set:
            prob += measure_power_consumption[f][m] == pulp.lpSum(
                -y_vars[f][m][t] * power_for_measure[f, m, i] * time_interval_duration_hours 
                for t in time_set 
                for i in max_lenght_of_measure_among_all_efdms 
                if (t + i - 1) < optimization_duration_intervals_num + 1)

    prob.solve(PULP_CBC_CMD(msg=0,timeLimit=300 )) #Use time limit for the server

    if LpStatus[prob.status] == "Infeasible":
        raise FileNotFoundError  
    
    if LpStatus[prob.status] == "Not Solved":
        raise FileNotFoundError

    Activated_measures_and_machines = []

    activated_measure_working_cost = {}
    activated_measure_cost = {}
    measure_power_consumption_dict = {}

    for v in prob.variables():
        if "cost_vars" in v.name:
            activated_measure_cost[v.name] = v.varValue

        if v.varValue != 0:
            Activated_measures_and_machines.extend([v.name])

        if "cost_act_vars" in v.name:
            activated_measure_working_cost[v.name] = v.varValue

        if "measure_power_consumption" in v.name:
            measure_power_consumption_dict[v.name] = v.varValue

    activated_measures = [
    (f, m, t)
    for f in flexibilities_set
    for m in measure_set
    for t in time_set
    if y_vars[f][m][t].value() == 1
                         ]
    Total_saving = pulp.value(prob.objective)
    calulation_outputs = {'Day_ahead_prices': electricity_price, 'totalSavings': Total_saving,
                          'totalEnergyConsumption': -sum(measure_power_consumption_dict.values()),
                          'activated_measures': activated_measures}
    
    return calulation_outputs, prob.sol_status



