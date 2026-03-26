def calculate_grams(quantity, unit, weight_per_unit):
    
    if unit == "piece":
        return quantity * weight_per_unit

    elif unit == "plate":
        return quantity * 6 * weight_per_unit

    elif unit == "half plate":
        return 3 * weight_per_unit

    elif unit == "bowl":
        return quantity * 200

    elif unit == "gram":
        return quantity

    else:
        return quantity * weight_per_unit