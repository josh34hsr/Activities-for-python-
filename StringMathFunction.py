expression = input("Enter a math expression (example: 3*5+2): ")

result = eval(expression, {"__builtins__": None}, {})

print("Result =", result)
