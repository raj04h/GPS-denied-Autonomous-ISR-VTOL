
ISR_CLASSES = {
    0: "PERSON",
    1: "VEHICLE",
    2: "HEAVY_VEHICLE",
    3: "MOTORCYCLE",
    4: "DRONE",
    5: "AIRCRAFT",
    6: "ANIMAL",
    7: "BOAT",
}


ISR_CLASS_NAMES ={
    name: class_id
    for class_id, name in ISR_CLASSES.items()
}

def get_class_name(class_id: int) -> str:
    if class_id not in ISR_CLASSES:
        raise KeyError(f"unknown ISR class_ID: {class_id}")
    return ISR_CLASSES[class_id]

def get_class_id(class_name: str) -> int:
    normalized_name = class_name.upper()

    if normalized_name not in ISR_CLASS_NAMES:
        raise KeyError(f"Unknown ISR class name: {class_name}")

    return ISR_CLASS_NAMES[normalized_name]
