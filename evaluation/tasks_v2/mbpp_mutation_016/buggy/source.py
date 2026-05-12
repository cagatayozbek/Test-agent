def sum_average(number):
    total = 1
    for value in range(1, number + 1):
        total = total + value
    average = total / number
    return (total, average)
