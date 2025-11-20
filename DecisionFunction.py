class BankAccount:
    def __init__(self,owner,balance=0):
        self.owner = owner
        self.balance = balance
    
        
    def deposit(self,amount):
        self.balance += amount
        print(f"{self.owner}deposited ₱{amount}. New balance: ₱{self.balance}")
    
    def withdraw(self,amount):
        if amount <= self.balance:
            self.balance -=  amount
            print(f"{self.owner} withdrew ₱{amount}.Remaining balance:₱{self.balance}")
        else:
            print("Insufficient Funds!")
            
account1= BankAccount("Jasmin" , 5000)
account1.deposit(1500)
account1.withdraw(2000)
account1.withdraw(6000)
