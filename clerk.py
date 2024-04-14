class Clerk():
    def __init__(self, id):
        self.salary = 2000 
        self.id = id  
        self.client = None 
        self.serve_time = None
        self.status = 'free' 

    def serve_client(self, client, time):
        """Начало обработки нового клиента"""
        self.client = client 
        self.serve_time = time
        self.status = 'busy'

    def make_step(self, on='work'):
        """Шаг обработки в 1 минуту"""
        if self.status == 'busy':
            self.serve_time -= 1 
            if self.serve_time == 0:
                self.status = 'free' if on == 'work' else on
                self.client.status = 'finish'
        elif self.status == 'free' and on != 'work':
            self.status = on