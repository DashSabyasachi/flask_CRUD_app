# Specific examples

import json

## json.dumps() — dict → JSON string (serialization)
data = {"name": "Rahul", "age": 25, "active": True}
json_string = json.dumps(data)
print(type(json_string))  # <class 'str'>


## json.dump() — dict → write to JSON file (serialization)
data = {"name": "Rahul", "age": 25}

with open("student.json", "w") as f:
    json.dump(data, f)
# Creates student.json file with JSON content


## json.loads() — JSON string → dict (deserialization)
json_string = '{"name": "Rahul", "age": 25, "active": true}'
data = json.loads(json_string)
print(type(data))   # <class 'dict'>
print(data["name"]) # Rahul


## json.load() — read JSON file → dict (deserialization)
with open("student.json", "r") as f:
    data = json.load(f)
print(type(data))   # <class 'dict'>
print(data["name"]) # Rahul

















