# A simple API method for now so we can start writing + running tests

def index():
    session.counter = (session.counter or 0) + 1
    return dict(counter=session.counter, now=request.now)
