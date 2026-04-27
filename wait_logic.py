def smart_wait(self):
    if not hasattr(self, 'wait_counter'): self.wait_counter = 0
    self.wait_counter += 1
    
    # لا يتكلم إلا مرة واحدة كل 20 دورة (تقريباً كل 15-20 ثانية)
    if self.wait_counter % 20 == 0:
        self.say("Take your time, I am watching you! 😊")
    elif self.wait_counter % 5 == 0:
        self.sigs.update_info.emit("Pepper: Waiting for your move... ⏳")
