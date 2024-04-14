from clerk import Clerk
from collections import deque

class Bank:
    def __init__(self, n_clerks, max_q_len, system):
        self.clerks = [Clerk(id) for id in range(n_clerks)]
        self.client_queue = deque()
        self.max_q_len = max_q_len
        self.statistics = {'profit': 0, 
                           'served_clients': 0,
                           'lost_clients': 0, 
                           'avg_waiting_time': 0, 
                           'avg_clerk_busy_time': 0,
                           'curr_q_len': 0,
                           'max_q_len': 0,
                           'min_q_len': 0,
                           'avg_q_len': 0}
        self.system = system
    
    def process_new_client(self, client):
        """Функция обработки нового клиента 
           Добавляем в очередь, либо клиент уходит при досотижении максимальной длины"""
        if len(self.client_queue) == self.max_q_len:
            self.statistics['lost_clients'] += 1
            return client
        else:
            self.client_queue.append(client)

    def make_step(self, on='work'):
        """Выполнение шага моделирования длиной в 1 минуту 
           Вызываем соответствующий метод для clerk'ов
           После этого отсматриваем есть ли свободные клерки, для них достаем из очереди клиентов и выполняем связывание
           Сохраняем данные (к примеру, длину очереди на текущей минуте) в статистиках для дальнейшего подсчета после выполнения шага"""
        new_serving_clients = []
        processed_clients = []
        for clerk in self.clerks:
            clerk.make_step(on)
            if clerk.status in {'free', on}:
                if clerk.client:
                    # collect info from served client
                    self.statistics['served_clients'] += 1
                    self.statistics['profit'] += clerk.client.profit
                    self.system.remove_tablo_line(clerk.client.id)
                    processed_clients.append(clerk.client)
                    clerk.client = None
                if clerk.status=='free' and self.client_queue:
                    new_client = self.client_queue.popleft()
                    self.system.add_info_tablo(new_client.id, clerk.id + 1)
                    serv_duration_time = self.system.randomizer.gen_serv_duration(self.system.distr, self.system.serv_duration_range)
                    new_client.start_serve(self.system.time, serv_duration_time)
                    clerk.serve_client(new_client, serv_duration_time)
        return processed_clients
    
    def drop_q(self):
        lost_clients = []
        self.statistics['lost_clients'] += len(self.client_queue)
        for client in self.client_queue:
            client.wait_time = self.system.time - client.start_time  
            client.status = 'lost'
            lost_clients.append(client)
        self.client_queue = deque()
        return lost_clients
    
    def start_work(self):
        if self.clerks[0].status in {'home', 'break'}:
            for clerk in self.clerks:
                clerk.status = 'free'