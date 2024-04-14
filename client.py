class Client:
    def __init__(self, id, start_time, profit):
        self.id = id
        self.status = 'waiting'
        self.start_time = start_time # client arrival time in min from system start 
        self.wait_time = None
        self.serve_time = None
        self.profit = profit

    def start_serve(self, curr_time, serve_time):
        """Начало обслуживания"""
        self.serve_time = serve_time
        self.wait_time = curr_time - self.start_time
        self.status = 'serving'