# manage.py
from getpass import getpass
from datetime import datetime
from flask_script import Manager, Command
from flask_migrate import Migrate, MigrateCommand

#from flask_script import Manager
#from flask_migrate import MigrateCommand

from OpenAgua import app, db
from OpenAgua.models import *

if __name__ == '__main__':
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    #app.config['SQLALCHEMY_DATABASE_URI'] = db_uri.replace('/../', '/./')

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)

@manager.command
def addsuperuser():
    '''
    Add a user with admin privledges.
    '''
    
    role = Role.query.filter(Role.name == 'admin').first()
    if not role:
        role = Role(name='admin')
        db.session.add(role)

    username = input("Username: ")
    
    user = User.query.filter(User.username == username).first()
    if user:
        print('User already exists. Exiting.')
        return
    
    email = input("Email: ")
    password1 = True
    password2 = False
    tries = 0
    maxtries = 3
    while not password1 == password2 and tries < maxtries:
        password1 = None
        while not password1:
            password1 = getpass("Password: ")
            if not password1:
                print("Password cannot be blank. Please try again.")
                tries += 1
            if tries == maxtries:
                break
        else:
            password2 = getpass("Verify password: ")
            if password2 != password1 and not failed:
                print("Passwords don't match. Please enter passwords again.")
                tries += 1
            
    if tries == maxtries:
        print('Max tries exceeded. Please start over.')
        return
    
    password = password1
    
    print("Creating account...", end=" ")
    
    # Create user
    user = User(username=username,
                email=email,
                password=app.user_manager.hash_password(password),
                active=True,
                confirmed_at=datetime.utcnow())

    # Bind admin to role
    user.roles.append(role)
    
    # Store user and roles
    db.session.add(user)
    db.session.commit()
    
    print("Done!")

if __name__ == "__main__":
    manager.run()