import json


with open("gt/283_ex1_gt.json", "r", encoding="utf-8") as f:
    gt_for_fields = json.load(f)


def normalize_keys(data):
    """
    Normalize keys in a dictionary by replacing curly quotes with straight quotes.
    """
    if isinstance(data, dict):
        return {
            key.replace("״", "\"").replace("'", "\""): normalize_keys(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    return data


def flatten_json(data, parent_key=""):
    """
    Flatten a nested JSON object into a single-level dictionary.
    """
    items = {}
    for key, value in data.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            # Do it recursively for nested dicts
            items.update(flatten_json(value, new_key))
        else:
            items[new_key] = value
    return items


def validate_with_ground_truth(json_data, ground_truth):
    """
    Validate extracted JSON against ground truth
    """

    validation_results = {
        "accuracy": 0.0,
        "completeness": 0.0,
        "missing_fields": [],
        "mismatched_fields": {}
    }
    json_data = normalize_keys(json_data)
    gt_data_n = normalize_keys(ground_truth)

    # Flatten both JSON data and ground truth
    flat_json_data = flatten_json(json_data)
    flat_ground_truth = flatten_json(gt_data_n)

    # Check for mismatched fields and missing fields
    correct_count = 0
    total_fields = len(flat_ground_truth)
    extracted_keys = set(flat_json_data.keys())
    gt_keys = set(flat_ground_truth.keys())
    missing_keys = gt_keys - extracted_keys

    for key, gt_value in flat_ground_truth.items():
        # Get the extracted value or use an empty string if not present
        extracted_value = flat_json_data.get(key, "")
        if extracted_value == gt_value:
            # Field matches in both dicts
            correct_count += 1
        else:
            # Field exists but mismatched
            validation_results["mismatched_fields"][key] = {
                "expected": gt_value,
                "actual": extracted_value
            }

    # Update results
    validation_results["missing_fields"] = list(missing_keys)

    # Calculate accuracy
    if total_fields > 0:
        validation_results["accuracy"] = (correct_count / total_fields) * 100

    # Calculate completeness
    validation_results["completeness"] = (
        (total_fields - len(missing_keys)) / total_fields * 100
    )

    return validation_results


def validate_dynamic_data(json_data):
    """
    Validate user-uploaded data for completeness and reasonableness.
    """
    validation_results = {
        "completeness": 0.0,
        "missing_fields": [],
        "invalid_fields": {},
    }

    json_data = normalize_keys(json_data)
    gt_data_n = normalize_keys(gt_for_fields)

    # Flatten JSON data
    flat_json_data = flatten_json(json_data)

    gt_keys = set(flatten_json(gt_data_n).keys())
    extracted_keys = set(flat_json_data.keys())
    missing_keys = gt_keys - extracted_keys

    validation_results["missing_fields"] = list(missing_keys)

    # Validate specific fields for correctness
    for field, value in flat_json_data.items():
        if "תאריך" in field and value:
            # Check for nested date fields
            if field.endswith("יום") or field.endswith("חודש"):
                if not value.isdigit() or int(value) <= 0:  # Ensure numeric and positive
                    validation_results["invalid_fields"][field] = "Invalid day or month value"
                if field.endswith("חודש") and int(value) > 12:
                    validation_results["invalid_fields"][field] = "Invalid month value"
            elif field.endswith("שנה"):
                if not value.isdigit() or len(value) != 4:
                    validation_results["invalid_fields"][field] = "Invalid year value"
        elif field == "מספר זהות" and value:
            # Validate ID number
            if not value.isdigit() or len(value) != 9:
                validation_results["invalid_fields"][field] = "Invalid ID number"
        elif field == "טלפון נייד" and value:
            # Validate phone number
            if not value.isdigit() or len(value) not in [9, 10]:
                validation_results["invalid_fields"][field] = "Invalid phone number"

    # Calculate completeness
    total_required = len(gt_keys)
    validation_results["completeness"] = (
            (total_required - len(missing_keys)) / total_required * 100
    )

    return validation_results


