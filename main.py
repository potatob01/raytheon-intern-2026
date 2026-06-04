data = []

with open("data.csv", "r") as file:
    # Throw out first two header rows
    file.readline()
    file.readline()

    # Iterate over each row and store into 2d array "data"
    for line in file:
        # strip() removes trailing newline
        data.append(line.strip().split(","))

key = input("Please enter a network activity name: ")

found = False

for line in data:
    if line[4] == key:
        print(f"Activity {key} is worth {line[7]} hours.")
        found = True
        break

if not found:
    print(f"Activity {key} was not found in the given data.")