import tkinter as tk 
from tkinter import ttk

from collections import deque

from bank import Bank
from client import Client 

from scipy.stats import truncnorm
import random
import numpy as np

WORK_HOURS = (10, 19)
WORK_HOURS_FR = (10, 17)
BREAK_HOURS = (12, 13)
MIN_PER_HOUR = 60
HOURS_PER_DAY = 24 

class Randomizer():
    def uniform_distr_value(self, range):
        """Генерирует число из равномерного распределения в границах"""
        return random.uniform(range[0], range[1])

    def normal_distr_value(self, range):
        """Генерирует число из нормального распределения в границах"""
        mean = (range[0] + range[1]) // 2
        sd = max((mean - range[0]) // 2, 1)
        return truncnorm((range[0] - mean) / sd, (range[1] - mean) / sd, loc=mean, scale=sd).rvs()

    def gen_profit(self, distr, profit_range):
        """Генерирование прибыли от пользователя"""
        if distr == 'uniform':
            gen_fun = self.uniform_distr_value
        elif distr == 'normal':
            gen_fun = self.normal_distr_value
        return gen_fun(profit_range)


    def gen_serv_duration(self, distr, serv_duration_range):
        """Генерирование времени обработки клиента (с последующей дискретизацией в минуты)"""
        if distr == 'uniform':
            gen_fun = self.uniform_distr_value
        elif distr == 'normal':
            gen_fun = self.normal_distr_value
        return round(gen_fun(serv_duration_range))

    def gen_period_between_clients(self, distr, query_range, time_coef, decrease_coef):
        """Генирирование промежутка между клиентами (с последующей дискретизацией в минуты)"""
        if distr == 'uniform':
            gen_fun = self.uniform_distr_value
        elif distr == 'normal':
            gen_fun = self.normal_distr_value

        val = round((1 + time_coef + decrease_coef) * gen_fun(query_range))
        return min(max(val, query_range[0]), query_range[1])


class System():
    def __init__(self):
        self.n_clerks = None
        self.clerks_range = (2, 7)
        self.date = None 
        self.time = None
        self.with_breaks = True 
        self.randomizer = Randomizer()

        self.max_queue_len = None

        self.distr = None
        self.query_range = None 
        self.profit_range = None 
        self.serv_duration_range = (2, 30)

        self.modeling_step = None
        self.modeling_period = 30 * HOURS_PER_DAY * MIN_PER_HOUR # месяц ~= 30 дней * 24 часа * 60 минут

        self.bank = None 

        self.time_to_client = None
        self.curr_client_id = 0
        self.processed_clients = []
        self.lost_clients = []
        self.q_lens = []
        self.clerk_busy_time = []
        
    def start_system(self):
        """Старт системы. Отрисовка основного интерфейса"""
        # ОКНО ПРИЛОЖЕНИЯ
        window = tk.Tk()
        window.title("Моделирование обслуживания в банке")
        window.resizable(width=False, height=False)
        window['bg'] = '#ffffff'
        self.window = window

        # Задание параметров
        left_frame = tk.Frame(window)
        left_frame.pack(side='left', padx=10, pady=10, fill=None, expand=False)

        label_left = tk.Label(left_frame, text="Параметры моделирования", font=('calibri', '18', 'bold'))
        label_left.pack()

        clerks_label = tk.Label(left_frame, text="Число клерков:")
        clerks_label.pack()
        self.clerks_var = tk.IntVar()
        self.clerks_var.set(3)
        clerks_options = list(range(self.clerks_range[0], self.clerks_range[1] + 1))
        clerks_optionmenu = tk.OptionMenu(left_frame, self.clerks_var, *clerks_options)
        clerks_optionmenu.pack()

        max_q_len_label = tk.Label(left_frame, text="Максимальная длина очереди:")
        max_q_len_label.pack()
        self.max_q_len_var = tk.IntVar()
        self.max_q_len_var.set(10)
        max_q_len_options = list(range(10, 16))
        max_q_len_optionmenu = tk.OptionMenu(left_frame, self.max_q_len_var, *max_q_len_options)
        max_q_len_optionmenu.pack()

        distribution_label = tk.Label(left_frame, text="Распределение:")
        distribution_label.pack()
        self.distribution_var = tk.StringVar()
        self.distribution_var.set('uniform')
        distribution_radio1 = tk.Radiobutton(left_frame, text="Равномерное", variable=self.distribution_var, value='uniform')
        distribution_radio1.pack()
        distribution_radio2 = tk.Radiobutton(left_frame, text="Нормальное", variable=self.distribution_var, value='normal')
        distribution_radio2.pack()

        time_label = tk.Label(left_frame, text="Промежуток времени между заявками")
        time_label.pack()

        row_frame = tk.Frame(left_frame)
        row_frame.pack()

        time_label2 = tk.Label(row_frame, text="        от")
        time_label2.pack(side='left')

        self.time_from_entry = tk.Entry(row_frame, width=5)
        self.time_from_entry.insert(0, "0")
        self.time_from_entry.pack(side='left')

        time_label3 = tk.Label(row_frame, text="мин        до")
        time_label3.pack(side='left')

        self.time_to_entry = tk.Entry(row_frame, width=5)
        self.time_to_entry.insert(0, "15")
        self.time_to_entry.pack(side='left')

        time_label4 = tk.Label(row_frame, text="мин")
        time_label4.pack(side='left')

        profit_label = tk.Label(left_frame, text="Прибыль от клиента")
        profit_label.pack()

        row_frame = tk.Frame(left_frame)
        row_frame.pack()

        profit_label2 = tk.Label(row_frame, text="от")
        profit_label2.pack(side='left')

        self.profit_from_entry = tk.Entry(row_frame, width=5)
        self.profit_from_entry.insert(0, "100")
        self.profit_from_entry.pack(side='left')

        profit_label3 = tk.Label(row_frame, text=" " * 15 + "до")
        profit_label3.pack(side='left')

        self.profit_to_entry = tk.Entry(row_frame, width=5)
        self.profit_to_entry.insert(0, "10000")
        self.profit_to_entry.pack(side='left')

        _ = tk.Label(left_frame, text="")
        _.pack(side='top')
        
        modeling_step_label = tk.Label(left_frame, text="Шаг моделирования:")
        modeling_step_label.pack()
        
        self.step_var = tk.StringVar()
        self.step_var.set('30 мин')
        step_options = ['1 мин', '5 мин', '30 мин', '1 час', '2 часа', '1 день']
        step_optionmenu = tk.OptionMenu(left_frame, self.step_var, *step_options)
        step_optionmenu.pack(side='top')

        _ = tk.Label(left_frame, text="")
        _.pack(side='top')

        frame_buttons = tk.Frame(left_frame)
        frame_buttons.pack()
        button_start = tk.Button(frame_buttons, text="начать", command=self.start_modeling)
        button_start.pack(side='left')
        button_start = tk.Button(frame_buttons, text="сделать шаг", command=self.make_step)
        button_start.pack(side='left')
        button_start = tk.Button(frame_buttons, text="до конца", command=self.make_all_steps)
        button_start.pack(side='left')


        self.right_frame = tk.Frame(self.window)
        self.right_frame.pack(side='left', padx=10, pady=10, fill=None, expand=False)

        window.mainloop()

    def start_modeling(self):
        """Старт моделирования. После нажатия на кнопну Начать
           Достаем основные параметры из введенных пользователями 
           Инициализируем основные классы"""
        
        # Get all entry values

        self.n_clerks = self.clerks_var.get()
        self.date = 1
        self.time = 10 * MIN_PER_HOUR # 10:00 1'st day
        self.max_queue_len = self.max_q_len_var.get()
        self.distr = self.distribution_var.get()
        self.query_range = (int(self.time_from_entry.get()), int(self.time_to_entry.get()))
        self.profit_range = (int(self.profit_from_entry.get()), int(self.profit_to_entry.get()))
        self.modeling_step = {"1 мин": 1, "5 мин": 5, "30 мин": 30, "1 час": 60, "2 часа": 120, "1 день": HOURS_PER_DAY * MIN_PER_HOUR}.get(self.step_var.get())
        self.bank = Bank(self.n_clerks, self.max_queue_len, self)

        # Right panel drawing

        self.datetime_var = tk.StringVar()
        self.recalc_datetime()
        time_label = tk.Label(self.right_frame, textvariable=self.datetime_var, font=('calibri', '14', 'bold'))
        time_label.pack(anchor='center')

        clerk_label = tk.Label(self.right_frame, text="Занятость клерков", font=('calibri', '14', 'bold'))
        clerk_label.pack(anchor='center')

        self.clerk_canvas = tk.Canvas(self.right_frame, width=200, height=50)
        self.clerk_canvas.pack(side='top', anchor='center')

        self.draw_clerks_status()
        
        title = tk.Label(self.right_frame, text=" " * 20 + "ИНФОРМАЦИОННОЕ TAБЛО" + " " * 20, font=('Calibri', 14, 'bold'))
        title.pack()
        frame_tablo = tk.Frame(self.right_frame, bg="black")
        frame_tablo.pack()

        scroll = tk.Scrollbar(frame_tablo)
        scroll.pack(side='right', fill=tk.Y) 

        self.table = ttk.Treeview(frame_tablo, yscrollcommand=scroll.set, style="mystyle.Treeview", height=4)
        scroll.config(command=self.table.yview)
        self.table.pack()

        self.table['columns'] = ["Клиент", "Номер окна"]
        self.table.column("#0", width=0, stretch=tk.NO)

        for column in self.table['columns']:
            self.table.column(column, anchor="w", width=150)

        self.table.heading("#0", text="", anchor=tk.CENTER)
        for column in self.table['columns']:
            self.table.heading(column, text=column, anchor=tk.CENTER)

        stats_label = tk.Label(self.right_frame, text="Статистики", font=('calibri', '14', 'bold'))
        stats_label.pack(anchor='center')

        frame_stats = tk.Frame(self.right_frame, bg="black")
        frame_stats.pack()

        scroll = tk.Scrollbar(frame_stats)
        scroll.pack(side='right', fill=tk.Y) 

        self.stats = ttk.Treeview(frame_stats, yscrollcommand=scroll.set, style="mystyle.Treeview", height=7)
        scroll.config(command=self.stats.yview)
        self.stats.pack()

        self.stats['columns'] = ["Статистика", "Значение"]
        self.stats.column("#0", width=0, stretch=tk.NO)

        
        self.stats.column("Статистика", anchor="w", width=200)
        self.stats.column("Значение", anchor="w", width=100)

        self.stats.heading("#0", text="", anchor=tk.CENTER)
        for column in self.stats['columns']:
            self.stats.heading(column, text=column, anchor=tk.CENTER)

        self.show_statistic(is_start=True)

    
    def recalc_datetime(self):
        """Перерисовка информации о дате и времени"""
        datetime = " " * 10 +f"# day {self.date} / time {self.time//60:02}:{self.time%60:02}"
        if self.date % 7 in {6, 0} or not (WORK_HOURS[0] <= self.time // MIN_PER_HOUR < WORK_HOURS[1]) or \
            (self.date % 7 == 5 and not(WORK_HOURS_FR[0] <= self.time // MIN_PER_HOUR < WORK_HOURS_FR[1])):
            datetime += "   ЗАКРЫТО"
        elif BREAK_HOURS[0] <= self.time // MIN_PER_HOUR < BREAK_HOURS[1]:
            datetime += "   ПЕРЕРЫВ"
        else:
            datetime += " " * 10
        self.datetime_var.set(datetime)

    def draw_clerks_status(self):
        """Отрисовка занятости клерков"""
        width = 15
        height = 20

        left_margin_base = 10 + (self.clerks_range[1] - self.n_clerks) * width 
        indent_down = 10

        internal_indent = 10

        for i in range(self.n_clerks):
            x0 = left_margin_base + i * (internal_indent + width)
            y0 = indent_down
            x1 = x0 + width
            y1 = y0 + height
            if self.bank.clerks[i].status == 'free':
                fill_color = 'green'
            elif self.bank.clerks[i].status in {'home', 'break'}:
                fill_color = 'grey'
            else:
                fill_color = 'red'

            self.clerk_canvas.create_rectangle(x0, y0, x1, y1, fill=fill_color)
            
            self.clerk_canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=str(i+1))

    def add_info_tablo(self, client_id, clerk_id):
        """Добавление информации на табло"""
        self.table.insert(parent='', index=0, text='', open=False,
                                        values=(client_id, clerk_id))
        
    def remove_tablo_line(self, client_id):
        items = self.table.get_children()
        for item in items:
            if self.table.item(item)["values"][0] == client_id:
                self.table.delete(item)
                break

    def make_step(self, check_modeling_step=True):
        """Моделирование 1 шага
           В зависимости от рандомного значения промежутка между клиентами, создаются новые клиенты и направляются в банк в очередь обработки
           Поминутно моделируются вызовы соответствующего метода для класса Bank"""  

        if check_modeling_step:
            self.modeling_step = {"1 мин": 1, "5 мин": 5, "30 мин": 30, "1 час": 60, "2 часа": 2 * MIN_PER_HOUR, "1 день": HOURS_PER_DAY * MIN_PER_HOUR}.get(self.step_var.get())
        for _ in range(self.modeling_step):
            if self.date % 7 in {6, 0} or not (WORK_HOURS[0] <= self.time // MIN_PER_HOUR < WORK_HOURS[1]) or \
                (self.date % 7 == 5 and not(WORK_HOURS_FR[0] <= self.time // MIN_PER_HOUR < WORK_HOURS_FR[1])):
                
                if (0 < self.date % 7 < 5 and self.time == WORK_HOURS[1] * MIN_PER_HOUR) or (self.date % 7 == 5 and self.time == WORK_HOURS_FR[1] * MIN_PER_HOUR):
                    self.calc_stats()  

                self.lost_clients.extend(self.bank.drop_q())
                self.time_to_client = None
                self.inc_time()
                processed_clients = self.bank.make_step('home')
                self.processed_clients.extend(processed_clients)           
                
            elif BREAK_HOURS[0] <= self.time // MIN_PER_HOUR < BREAK_HOURS[1]:
                self.inc_time()
                self.time_to_client = None
                processed_clients = self.bank.make_step('break')
                self.processed_clients.extend(processed_clients)

            else:
                self.bank.start_work()
                if self.time_to_client is None:
                    self.time_to_client = self.randomizer.gen_period_between_clients(self.distr, self.query_range, self.calc_time_coef(), self.calc_decrease_coef())
                while self.time_to_client == 0:
                    profit = self.randomizer.gen_profit(self.distr, self.profit_range)
                    lost_client = self.bank.process_new_client(Client(self.curr_client_id, self.time, profit))
                    if lost_client:
                        lost_client.status = 'lost'
                        lost_client.wait_time = 0
                        self.lost_clients.append(lost_client)
                    self.curr_client_id += 1
                    self.time_to_client = self.randomizer.gen_period_between_clients(self.distr, self.query_range, self.calc_time_coef(), self.calc_decrease_coef())
                processed_clients = self.bank.make_step()
                self.processed_clients.extend(processed_clients)
                for client in processed_clients:
                    self.remove_tablo_line(client.id)
                
                self.inc_time()
                self.time_to_client -= 1
                self.q_lens.append(len(self.bank.client_queue))
                self.clerk_busy_time.append(sum([clerk.status == 'busy' for clerk in self.bank.clerks]))
    
        self.recalc_datetime()
        self.draw_clerks_status() 
        self.calc_stats()
        self.show_statistic()    
    
    def inc_time(self):
        """+ 1 минута к текущему времени"""
        if self.time == 23 * MIN_PER_HOUR + 59:
            self.time = 0
            self.date += 1 
        else:
            self.time += 1
        

    def make_all_steps(self):
        """Моделирование до конца периода"""
        self.modeling_step = (31 - self.date) * HOURS_PER_DAY * MIN_PER_HOUR + 10 * MIN_PER_HOUR - self.time 
        self.make_step(False)

    def calc_time_coef(self):
        """Расчет коэффициента для генерации промежутка между людьми, который задает зависимость потока от текщего дня и времени"""
        coef = 0
        if self.date % 5 == 0:
            coef -= 1 / (self.query_range[1] - self.query_range[0])
        if self.time >= 16 * MIN_PER_HOUR:
            coef -= 2 / (self.query_range[1] - self.query_range[0])
        return coef

    def calc_decrease_coef(self):
        """Расчет коэффициента для генерации промежутка между людьми, который задает зависимость от длины очереди и числа потерянных клиентов"""
        return (len(self.lost_clients) / 100 + len(self.bank.client_queue) / 3) / (self.query_range[1] - self.query_range[0])

    def calc_stats(self):
        """Пересчет статистик после очередного шага моделирования"""
        if (0 < self.date % 7 < 5 and self.time == WORK_HOURS[1] * MIN_PER_HOUR) or (self.date % 7 == 5 and self.time == WORK_HOURS_FR[1] * MIN_PER_HOUR):
            self.bank.statistics['profit'] -= 2000 * self.n_clerks # salary
        self.bank.statistics['max_q_len'] = max(self.q_lens)
        self.bank.statistics['min_q_len'] = min(self.q_lens)
        self.bank.statistics['avg_q_len'] = round(np.mean(self.q_lens), 3)
        self.bank.statistics['curr_q_len'] = self.q_lens[-1]
        
        sum_waiting_time = 0 
        client_num = len(self.processed_clients)
        for client in self.processed_clients:
            sum_waiting_time += client.wait_time

        for client in self.lost_clients:
            if client.wait_time:
                sum_waiting_time += client.wait_time
                client_num += 1
        
        for clerk in self.bank.clerks:
            if clerk.client:
                sum_waiting_time += clerk.client.wait_time
                client_num += 1

        self.bank.statistics['avg_waiting_time'] = round(sum_waiting_time / max(client_num, 1), 3)

        work_time = 0
        for d in range(1, self.date):
            if d % 7 in {6, 0}: 
                continue
            elif d % 7 == 5:
                work_time += 6 * MIN_PER_HOUR
            else:
                work_time += 8 * MIN_PER_HOUR
        if self.date % 7 == 5:
            if 10 * MIN_PER_HOUR <= self.time <= BREAK_HOURS[0] * MIN_PER_HOUR:
                work_time += self.time - 10 * MIN_PER_HOUR
            elif BREAK_HOURS[0] * MIN_PER_HOUR <= self.time <= WORK_HOURS_FR[1] * MIN_PER_HOUR:
                work_time += 2 * MIN_PER_HOUR + max(self.time - BREAK_HOURS[1] * MIN_PER_HOUR, 0)
            elif self.time > WORK_HOURS_FR[1] * MIN_PER_HOUR:
                work_time += 6 * MIN_PER_HOUR
        elif 0 < self.date % 7 < 5:
            if WORK_HOURS[0] * MIN_PER_HOUR <= self.time <= BREAK_HOURS[0] * MIN_PER_HOUR:
                work_time += self.time - 10 * MIN_PER_HOUR
            elif BREAK_HOURS[0] * MIN_PER_HOUR <= self.time <= WORK_HOURS[1] * MIN_PER_HOUR:
                work_time += 2 * MIN_PER_HOUR + max(self.time - BREAK_HOURS[1] * MIN_PER_HOUR, 0)
            elif self.time > WORK_HOURS[1] * MIN_PER_HOUR:
                work_time += 8 * MIN_PER_HOUR

        self.bank.statistics['avg_clerk_busy_time'] = round(sum(self.clerk_busy_time) / (self.n_clerks * work_time), 3)
 
    def show_statistic(self, is_start=False):
        """Отрисовка новых статистик"""
        name_mapper = {'served_clients': 'обслуженных клиентов',
                       'lost_clients': 'потерянных клиентов',
                       'curr_q_len': 'текущая длина очереди', 
                       'max_q_len': 'максимальная длина очереди', 
                       'min_q_len': 'минимальная длина очереди',
                       'avg_q_len': 'средняя длина очереди',
                       'avg_waiting_time': 'среднее время ожидания',
                       'avg_clerk_busy_time': 'средняя занятость клерков',
                       'profit':'прибыль'}
        self.bank.statistics['profit'] = round(self.bank.statistics['profit'])
        if is_start:
            for i, (stat, val) in enumerate(self.bank.statistics.items()):
                self.stats.insert(parent='', index=i, text='', open=False,
                                            values=(name_mapper[stat], val))
        else:
            items = self.stats.get_children()
            for item, (stat, new_val) in zip(items, self.bank.statistics.items()):
                self.stats.item(item, values=(name_mapper[stat], new_val))

if __name__ == '__main__':
    System().start_system()