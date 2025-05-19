import queue
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

import customtkinter as ctk

# Simulation constants
LIGHT_DURATION = 5
CAR_CROSSING_TIME = 2
UPDATE_INTERVAL = 100
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 500
ROAD_WIDTH = 50
CAR_SIZE = 25
MAX_WAITING_TIME = 30
SAFE_DISTANCE = 10

# UI colors
COLORS = {
    "bg": "#2b2b2b",
    "fg": "#ffffff",
    "accent": "#007AFF",
    "road": "#404040",
    "car1": "#FF6B6B",
    "car2": "#4ECDC4",
    "light_red": "#FF4444",
    "light_yellow": "#FFD700",
    "light_green": "#00C851",
    "light_off": "#666666"
}

class LightState(Enum):
    RED = "RED"
    GREEN = "GREEN"
    YELLOW = "YELLOW"

@dataclass
class Car:
    id: int
    road_num: int
    position: float
    speed: float
    waiting_time: float
    state: str

@dataclass
class Road:
    name: str
    light_state: LightState
    cars: List[Car]
    lock: threading.Lock
    condition: threading.Condition
    semaphore: threading.Semaphore
    last_light_change: float
    queue_length: int

class TrafficSimulator:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Traffic Light Synchronization Simulator")
        self.root.geometry("1000x800")
        self.root.configure(fg_color=COLORS["bg"])
        
        self.is_running = False
        self.simulation_thread: Optional[threading.Thread] = None
        self.car_threads: List[threading.Thread] = []
        self.case_type = 1
        self.start_time = time.time()
        
        self.message_queue = queue.Queue()
        
        self.roads: Dict[int, Road] = {
            1: Road("Road 1", LightState.RED, [], threading.Lock(), 
                    threading.Condition(threading.Lock()), threading.Semaphore(1),
                    time.time(), 0),
            2: Road("Road 2", LightState.RED, [], threading.Lock(),
                    threading.Condition(threading.Lock()), threading.Semaphore(1),
                    time.time(), 0)
        }
        
        self.case_var = ctk.StringVar(value="1")
        self.cars_entry: Optional[ctk.CTkEntry] = None
        self.k_entry: Optional[ctk.CTkEntry] = None
        self.start_button: Optional[ctk.CTkButton] = None
        self.canvas: Optional[ctk.CTkCanvas] = None
        self.road1_frame: Optional[ctk.CTkFrame] = None
        self.road2_frame: Optional[ctk.CTkFrame] = None
        self.log_text: Optional[ctk.CTkTextbox] = None
        
        self.light_thread: Optional[threading.Thread] = None
        self.display_thread: Optional[threading.Thread] = None
        
        self.setup_gui()
        self.process_messages()

    def setup_gui(self):
        # Title Frame
        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.pack(pady=10)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="Traffic Light Synchronization Simulator",
            font=("Helvetica", 24, "bold"),
            text_color=COLORS["accent"]
        )
        title_label.pack()
        
        # Control Frame
        control_frame = ctk.CTkFrame(self.root, fg_color="#333333", corner_radius=10)
        control_frame.pack(pady=5, padx=20, fill="x")
        
        # Case Selection
        case_label = ctk.CTkLabel(
            control_frame,
            text="Select Case:",
            font=("Helvetica", 14),
            text_color=COLORS["fg"]
        )
        case_label.pack(side="left", padx=15)
        
        case1_radio = ctk.CTkRadioButton(
            control_frame,
            text="Case 1 (Single Car)",
            variable=self.case_var,
            value="1",
            font=("Helvetica", 12),
            fg_color=COLORS["accent"]
        )
        case2_radio = ctk.CTkRadioButton(
            control_frame,
            text="Case 2 (Multiple Cars)",
            variable=self.case_var,
            value="2",
            font=("Helvetica", 12),
            fg_color=COLORS["accent"]
        )
        case1_radio.pack(side="left", padx=10)
        case2_radio.pack(side="left", padx=10)
        
        # Number of cars input
        cars_label = ctk.CTkLabel(
            control_frame,
            text="Number of Cars:",
            font=("Helvetica", 14),
            text_color=COLORS["fg"]
        )
        cars_label.pack(side="left", padx=15)
        
        self.cars_entry = ctk.CTkEntry(
            control_frame,
            width=60,
            height=30,
            font=("Helvetica", 12),
            fg_color="#404040",
            border_color=COLORS["accent"]
        )
        self.cars_entry.pack(side="left", padx=5)
        self.cars_entry.insert(0, "10")
        
        # K value input
        k_label = ctk.CTkLabel(
            control_frame,
            text="K value:",
            font=("Helvetica", 14),
            text_color=COLORS["fg"]
        )
        k_label.pack(side="left", padx=15)
        
        self.k_entry = ctk.CTkEntry(
            control_frame,
            width=60,
            height=30,
            font=("Helvetica", 12),
            fg_color="#404040",
            border_color=COLORS["accent"]
        )
        self.k_entry.pack(side="left", padx=5)
        self.k_entry.insert(0, "3")
        
        # Start/Stop button
        self.start_button = ctk.CTkButton(
            control_frame,
            text="Start Simulation",
            command=self.toggle_simulation,
            font=("Helvetica", 14, "bold"),
            fg_color=COLORS["accent"],
            hover_color="#0056b3",
            height=40,
            width=150
        )
        self.start_button.pack(side="right", padx=15)
        
        # Main content frame (simulation + road status)
        main_content = ctk.CTkFrame(self.root, fg_color="transparent")
        main_content.pack(pady=5, padx=20, fill="both", expand=True)
        
        # Left side - Simulation Frame
        sim_frame = ctk.CTkFrame(main_content, fg_color="#333333", corner_radius=10)
        sim_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Visualization Canvas
        self.canvas = ctk.CTkCanvas(
            sim_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=COLORS["bg"],
            highlightthickness=0
        )
        self.canvas.pack(pady=10, padx=10)
        
        # Right side - Road Status Frame (more compact)
        road_status_frame = ctk.CTkFrame(main_content, fg_color="#333333", corner_radius=10)
        road_status_frame.pack(side="right", fill="y", expand=False, padx=(10, 0), pady=10)
        
        # Road 1 Frame
        self.road1_frame = ctk.CTkFrame(road_status_frame, fg_color="transparent")
        self.road1_frame.pack(fill="x", expand=False, padx=5, pady=5)
        
        # Road 2 Frame
        self.road2_frame = ctk.CTkFrame(road_status_frame, fg_color="transparent")
        self.road2_frame.pack(fill="x", expand=False, padx=5, pady=5)
        
        # Add separator between road frames
        separator = ctk.CTkFrame(road_status_frame, height=2, fg_color="#404040")
        separator.pack(fill="x", padx=10, pady=5)
        
        # Setup road displays
        self.setup_road_display(1)
        self.setup_road_display(2)
        
        # Log Frame (larger)
        log_frame = ctk.CTkFrame(self.root, fg_color="#333333", corner_radius=10)
        log_frame.pack(pady=5, padx=20, fill="both", expand=True)
        
        # Log title
        log_title = ctk.CTkLabel(
            log_frame,
            text="Simulation Log",
            font=("Helvetica", 16, "bold"),
            text_color=COLORS["accent"]
        )
        log_title.pack(pady=5)
        
        # Log text (taller)
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=200,  # Increased height
            font=("Consolas", 12),
            fg_color="#404040",
            text_color=COLORS["fg"]
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Initialize visualization
        self.draw_roads()
        
    def setup_road_display(self, road_num: int):
        frame = self.road1_frame if road_num == 1 else self.road2_frame
        
        # Create a container frame for vertical layout
        container = ctk.CTkFrame(frame, fg_color="transparent")
        container.pack(expand=True, fill="x", padx=5, pady=2)
        
        # Road label with larger font
        road_label = ctk.CTkLabel(
            container,
            text=f"Road {road_num}",
            font=("Helvetica", 14, "bold"),
            text_color=COLORS["accent"]
        )
        road_label.pack(pady=(0, 5))
        
        # Traffic light status frame
        light_frame = ctk.CTkFrame(container, fg_color="#404040", corner_radius=8)
        light_frame.pack(fill="x", pady=2)
        
        light_label = ctk.CTkLabel(
            light_frame,
            text=self.roads[road_num].light_state.value,
            font=("Helvetica", 16, "bold")
        )
        light_label.pack(pady=2)
        setattr(self, f"light_label_{road_num}", light_label)
        
        # Car status frame
        car_status_frame = ctk.CTkFrame(container, fg_color="#404040", corner_radius=8)
        car_status_frame.pack(fill="x", pady=2)
        
        # Waiting cars
        waiting_frame = ctk.CTkFrame(car_status_frame, fg_color="transparent")
        waiting_frame.pack(fill="x", pady=2)
        
        waiting_label = ctk.CTkLabel(
            waiting_frame,
            text="Waiting:",
            font=("Helvetica", 12),
            text_color=COLORS["fg"]
        )
        waiting_label.pack(side="left", padx=5)
        
        waiting_cars = ctk.CTkLabel(
            waiting_frame,
            text="0",
            font=("Helvetica", 12, "bold"),
            text_color=COLORS["accent"]
        )
        waiting_cars.pack(side="right", padx=5)
        setattr(self, f"waiting_cars_{road_num}", waiting_cars)
        
        # Crossing cars
        crossing_frame = ctk.CTkFrame(car_status_frame, fg_color="transparent")
        crossing_frame.pack(fill="x", pady=2)
        
        crossing_label = ctk.CTkLabel(
            crossing_frame,
            text="Crossing:",
            font=("Helvetica", 12),
            text_color=COLORS["fg"]
        )
        crossing_label.pack(side="left", padx=5)
        
        crossing_cars = ctk.CTkLabel(
            crossing_frame,
            text="0",
            font=("Helvetica", 12, "bold"),
            text_color=COLORS["accent"]
        )
        crossing_cars.pack(side="right", padx=5)
        setattr(self, f"crossing_cars_{road_num}", crossing_cars)

    def process_messages(self) -> None:
        try:
            while True:
                message = self.message_queue.get_nowait()
                if message["type"] == "log":
                    self.log_text.insert("end", f"{message['content']}\n")
                    self.log_text.see("end")
                elif message["type"] == "update_display":
                    self.update_gui_display()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_messages)

    def update_gui_display(self) -> None:
        self.canvas.delete("car")
        
        for road_num in [1, 2]:
            road = self.roads[road_num]
            with road.lock:
                light_label = getattr(self, f"light_label_{road_num}")
                waiting_cars = getattr(self, f"waiting_cars_{road_num}")
                crossing_cars = getattr(self, f"crossing_cars_{road_num}")
                
                light_label.configure(text=road.light_state.value)
                light_label.configure(text_color=road.light_state.name.lower())
                
                waiting_cars.configure(text=str(len([c for c in road.cars if c.state == "waiting"])))
                crossing_cars.configure(text=str(len([c for c in road.cars if c.state == "crossing"])))
                
                red_light = getattr(self, f"red_light_{road_num}")
                green_light = getattr(self, f"green_light_{road_num}")
                
                if road.light_state == LightState.RED:
                    self.canvas.itemconfig(red_light, fill="red")
                    self.canvas.itemconfig(green_light, fill="gray")
                elif road.light_state == LightState.YELLOW:
                    self.canvas.itemconfig(red_light, fill="yellow")
                    self.canvas.itemconfig(green_light, fill="gray")
                else:
                    self.canvas.itemconfig(red_light, fill="gray")
                    self.canvas.itemconfig(green_light, fill="green")
                
                for car in road.cars:
                    if car.state != "exited":
                        if road_num == 1:
                            x = car.position * (CANVAS_WIDTH - ROAD_WIDTH) + ROAD_WIDTH//2
                            y = CANVAS_HEIGHT//2
                        else:
                            x = CANVAS_WIDTH//2
                            y = car.position * (CANVAS_HEIGHT - ROAD_WIDTH) + ROAD_WIDTH//2
                        self.draw_car(car.id, road_num, x, y)

    def log(self, message: str) -> None:
        self.message_queue.put({"type": "log", "content": message})

    def update_display(self) -> None:
        while self.is_running:
            self.message_queue.put({"type": "update_display"})
            time.sleep(UPDATE_INTERVAL / 1000)

    def draw_roads(self):
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw horizontal road (Road 1)
        self.canvas.create_rectangle(
            0, CANVAS_HEIGHT//2 - ROAD_WIDTH//2,
            CANVAS_WIDTH, CANVAS_HEIGHT//2 + ROAD_WIDTH//2,
            fill=COLORS["road"], outline=""
        )
        
        # Draw vertical road (Road 2)
        self.canvas.create_rectangle(
            CANVAS_WIDTH//2 - ROAD_WIDTH//2, 0,
            CANVAS_WIDTH//2 + ROAD_WIDTH//2, CANVAS_HEIGHT,
            fill=COLORS["road"], outline=""
        )
        
        # Draw traffic lights at the intersection
        # Road 1 (Horizontal) - Left side of intersection
        self.draw_traffic_light(1, CANVAS_WIDTH//2 - ROAD_WIDTH - 40, CANVAS_HEIGHT//2 - 40)
        # Road 2 (Vertical) - Top of intersection
        self.draw_traffic_light(2, CANVAS_WIDTH//2 - 40, CANVAS_HEIGHT//2 - ROAD_WIDTH - 40)
        
    def draw_traffic_light(self, road_num, x, y):
        # Draw traffic light housing
        self.canvas.create_rectangle(
            x, y, x + 30, y + 80,
            fill="#1a1a1a",
            outline="#333333",
            width=2
        )
        
        # Draw light circles with glow effect
        red_light = self.canvas.create_oval(
            x + 5, y + 5,
            x + 25, y + 25,
            fill=COLORS["light_red"],
            outline=""
        )
        green_light = self.canvas.create_oval(
            x + 5, y + 55,
            x + 25, y + 75,
            fill=COLORS["light_off"],
            outline=""
        )
        
        # Store light references
        setattr(self, f"red_light_{road_num}", red_light)
        setattr(self, f"green_light_{road_num}", green_light)

    def draw_car(self, car_id, road_num, x, y):
        """Draw a car at the specified position"""
        color = COLORS["car1"] if road_num == 1 else COLORS["car2"]
        
        # Draw car body with rounded corners
        self.canvas.create_rectangle(
            x - CAR_SIZE//2, y - CAR_SIZE//2,
            x + CAR_SIZE//2, y + CAR_SIZE//2,
            fill=color,
            outline="#1a1a1a",
            width=2,
            tags="car"
        )
        
        # Draw car windows
        window_size = CAR_SIZE//3
        self.canvas.create_rectangle(
            x - window_size//2, y - window_size//2,
            x + window_size//2, y + window_size//2,
            fill="#ffffff",
            outline="#1a1a1a",
            width=1,
            tags="car"
        )
        
        # Draw car number with better visibility
        self.canvas.create_oval(
            x - 10, y - 10,
            x + 10, y + 10,
            fill="#1a1a1a",
            outline="",
            tags="car"
        )
        
        self.canvas.create_text(
            x, y,
            text=str(car_id),
            fill="#ffffff",
            font=("Helvetica", 12, "bold"),
            tags="car"
        )

    def car_process(self, car_id: int, road_num: int) -> None:
        road = self.roads[road_num]
        car = Car(car_id, road_num, 0.0, 0.0, 0.0, "waiting")
        
        with road.lock:
            road.cars.append(car)
            self.log(f"Car {car_id} arrived on Road {road_num}")
        
        while self.is_running and car.state != "exited":
            with road.condition:
                if road.light_state == LightState.GREEN or road.light_state == LightState.YELLOW:
                    if self.can_cross(road, car):
                        car.state = "crossing"
                        self.log(f"Car {car_id} started crossing on Road {road_num}")
                        break
                
                road.condition.wait()
                car.waiting_time += 0.1
                if car.waiting_time > MAX_WAITING_TIME:
                    self.log(f"Car {car_id} has been waiting too long on Road {road_num}")
                    break
        
        if car.state == "crossing":
            start_time = time.time()
            while time.time() - start_time < CAR_CROSSING_TIME:
                car.position += 0.1
                time.sleep(0.1)
            
            with road.lock:
                if car in road.cars:
                    road.cars.remove(car)
                car.state = "exited"
                self.log(f"Car {car_id} finished crossing on Road {road_num}")

    def can_cross(self, road: Road, car: Car) -> bool:
        if self.case_type == 1:
            return not any(c.state == "crossing" for c in road.cars)
        
        k = int(self.k_entry.get())
        crossing_cars = [c for c in road.cars if c.state == "crossing"]
        
        # If no cars are crossing, allow the car to cross
        if not crossing_cars:
            return True
            
        # Check if we've reached the maximum number of crossing cars
        if len(crossing_cars) >= k:
            return False
        
        # Allow crossing if there's space
        if car.position == 0:
            return True
            
        # For cars that are already crossing, check distance from the last crossing car
        last_car = max(crossing_cars, key=lambda c: c.position)
        min_distance = SAFE_DISTANCE / CANVAS_WIDTH
        
        # Allow crossing if the car is far enough from the last crossing car
        return car.position - last_car.position >= min_distance

    def traffic_light_process(self) -> None:
        while self.is_running:
            for road_num in [1, 2]:
                if not self.is_running:
                    break
                    
                road = self.roads[road_num]
                current_time = time.time()
                
                with road.condition:
                    road.light_state = LightState.GREEN
                    road.last_light_change = current_time
                    self.log(f"Road {road_num} light turned GREEN")
                    road.condition.notify_all()
                
                time.sleep(LIGHT_DURATION)
                
                with road.condition:
                    road.light_state = LightState.YELLOW
                    self.log(f"Road {road_num} light turned YELLOW")
                    road.condition.notify_all()
                
                time.sleep(1)
                
                with road.condition:
                    road.light_state = LightState.RED
                    self.log(f"Road {road_num} light turned RED")
                    road.condition.notify_all()

    def toggle_simulation(self) -> None:
        if not self.is_running:
            self.start_simulation()
        else:
            self.stop_simulation()
            
    def start_simulation(self) -> None:
        self.is_running = True
        self.case_type = int(self.case_var.get())
        num_cars = int(self.cars_entry.get())
        
        self.canvas.delete("car")
        self.car_threads.clear()
        
        for road in self.roads.values():
            with road.condition:
                road.cars.clear()
                road.light_state = LightState.RED
                road.condition.notify_all()
        
        self.log_text.delete("1.0", "end")
        self.log("Starting new simulation...")
        
        self.light_thread = threading.Thread(target=self.traffic_light_process)
        self.light_thread.daemon = True
        self.light_thread.start()
        
        self.display_thread = threading.Thread(target=self.update_display)
        self.display_thread.daemon = True
        self.display_thread.start()
        
        for i in range(num_cars):
            road_num = random.randint(1, 2)
            car_thread = threading.Thread(target=self.car_process, args=(i+1, road_num))
            car_thread.daemon = True
            car_thread.start()
            self.car_threads.append(car_thread)
            
        self.start_button.configure(text="Stop Simulation")
        
    def stop_simulation(self) -> None:
        self.is_running = False
        self.start_button.configure(text="Start Simulation")
        
        self.canvas.delete("car")
        self.car_threads.clear()
        
        for road in self.roads.values():
            with road.condition:
                road.cars.clear()
                road.light_state = LightState.RED
                road.condition.notify_all()
        
        self.log("Simulation stopped")
        
        if self.light_thread:
            self.light_thread.join(timeout=1.0)
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
            
    def run(self) -> None:
        self.root.mainloop()

if __name__ == "__main__":
    app = TrafficSimulator()
    app.run()
    