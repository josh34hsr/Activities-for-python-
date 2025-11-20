def calculator():
    print("Mini Calculator")
    print("Operations: +  -  *  /  **  %")

    num1 = float(input("Enter first number: "))
    op = input("Enter operator: ")
    num2 = float(input("Enter second number: "))

    if op == "+":
        result = num1 + num2
    elif op == "-":
        result = num1 - num2
    elif op == "*":
        result = num1 * num2
    elif op == "/":
        result = num1 / num2 if num2 != 0 else "Undefined (division by zero)"
    elif op == "**":
        result = num1 ** num2
    elif op == "%":
        result = num1 % num2
    else:
        result = "Invalid operator"

    print("Result:", result)

calculator()
