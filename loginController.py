import pandas as pd

class LoginController:
    def __init__(self, uname, password):
        self.uname = uname
        self.password = password
        self.loggedin = False
        
    def login(self):
        if self.uname == 'admin' and self.password == 'admin':
            self.loggedin = True
        else:
            self.loggedin = False
        
    def logout(self):
        self.loggedin = False
        self.uname = ""
        self.password = ""
        self.names = []
        self.indeces = []
        self.timestamps = []
        