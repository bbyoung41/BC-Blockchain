import random

def Tracking():
    Response = 'Pending'
    while Response == 'Pending':
        Response = Validate()
        print('waiting for response')

    print(f'Transaction is {Response}')

def Validate():
    responses = ['Valid', 'Invalid', 'Pending']
    a = random.choice(responses)
    print(a)
    return a

Tracking()