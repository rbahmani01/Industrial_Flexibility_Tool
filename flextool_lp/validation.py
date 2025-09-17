# Helper to convert keys like "(1,1,2)" → (1,1,2)
def tuple_key(k):
    if k.startswith("(") and k.endswith(")"):
        return tuple(map(int, k.strip("()").split(",")))
    return int(k) if k.isdigit() else k

# Convert dictionary keys
def convert_keys(d):
    return {tuple_key(k): v for k, v in d.items()}

def reformat_payload(data):
    # Convert all sections
    data["electricity_price"] = {int(k): v for k, v in data["electricity_price"].items()}
    data["start_cost"] = convert_keys(data["start_cost"])
    data["power_for_measure"] = convert_keys(data["power_for_measure"])
    data["time_length_of_measure"] = convert_keys(data["time_length_of_measure"])
    data["regeneration_time"] = convert_keys(data["regeneration_time"])
    return data
