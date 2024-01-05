class Progress:
    start = 0
    end = 0
    update_interval = 25
    timer = start

    def calibrate(self, ids, update_interval):
        self.end = len(ids)
        self.update_interval = update_interval

    def progress(self):
        if self.timer % self.update_interval == 0:
            print(f"{round((self.timer / self.end)*100, 2)}% completed.")

    def next(self):
        self.timer = self.timer + 1
