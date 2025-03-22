import random
import numpy as np
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import re

# Thêm CSS tùy chỉnh
st.markdown("""
    <style>
    .main { background-color: #0aaf8e; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2); color: white; }
    .stButton>button { background-color: #ff7675; color: white; border: none; border-radius: 5px; padding: 10px 20px; cursor: pointer; transition: transform 0.2s ease, background-color 0.3s ease; }
    .stButton>button:hover { background-color: #d63031; transform: scale(1.05); }
    .stTextInput>div>input, .stNumberInput>div>input, .stTextArea>div>textarea { border: 2px solid #ffffff; border-radius: 10px; padding: 10px; box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.1); transition: box-shadow 0.3s ease; }
    .stTextInput>div>input:focus, .stNumberInput>div>input:focus, .stTextArea>div>textarea:focus { box-shadow: 0 0 10px rgba(255, 255, 255, 0.8); border-color: #ffffff; }
    h1, h2, h3 { color: #ffffff; font-family: 'Arial', sans-serif; text-align: center; font-weight: bold; text-shadow: 2px 2px rgba(0, 0, 0, 0.2); }
    .sidebar .sidebar-content { background-color: #16d39a; border-radius: 10px; padding: 15px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2); color: white; }
    </style>
""", unsafe_allow_html=True)

# Đường dẫn file lưu lịch sử lịch học
HISTORY_FILE = "schedule_history.json"

# Giả định mỗi tiết học là 50 phút
LESSON_DURATION = 50  # phút

# Ánh xạ ngày tiếng Việt sang tiếng Anh
DAY_MAPPING = {
    "Thứ 2": "Monday",
    "Thứ 3": "Tuesday",
    "Thứ 4": "Wednesday",
    "Thứ 5": "Thursday",
    "Thứ 6": "Friday",
    "Thứ 7": "Saturday",
    "Thứ CN": "Sunday"
}

# Hàm kiểm tra định dạng thời gian rảnh
def validate_time_format(time_str):
    pattern = r"^(Thứ [2-7]|Thứ CN)-([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    times = [t.strip() for t in time_str.split(",") if t.strip()]
    for t in times:
        if not re.match(pattern, t):
            return False
        try:
            start_dt, end_dt = parse_time_slot(t)
            if start_dt >= end_dt:
                return False
        except ValueError:
            return False
    return True

# Hàm kiểm tra tên không chứa ký tự đặc biệt, nhưng cho phép ký tự tiếng Việt
def validate_name(name):
    pattern = r"^[a-zA-Z0-9\s\u00C0-\u1EF9]+$"
    return bool(re.match(pattern, name))

# Hàm chuyển đổi thời gian từ chuỗi tiếng Việt sang datetime
def parse_time_slot(time_str):
    day_vn, times = time_str.split("-", 1)
    start_time, end_time = times.split("-")
    day_en = DAY_MAPPING[day_vn]
    start_dt = datetime.strptime(f"{day_en} {start_time}", "%A %H:%M")
    end_dt = datetime.strptime(f"{day_en} {end_time}", "%A %H:%M")
    return start_dt, end_dt

# Tính thời lượng cần thiết từ số tiết
def calculate_duration_minutes(duration_lessons):
    return duration_lessons * LESSON_DURATION

# Kiểm tra thời gian rảnh có đủ cho số tiết không
def is_time_slot_sufficient(teacher_time, required_minutes):
    start_dt, end_dt = parse_time_slot(teacher_time)
    available_minutes = int((end_dt - start_dt).total_seconds() / 60)
    return available_minutes >= required_minutes

# Hàm lưu lịch sử lịch học vào JSON
def save_history(schedule):
    # Đọc lịch sử hiện có (nếu có)
    history_list = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Nếu dữ liệu cũ là một dictionary (cấu trúc cũ), chuyển thành list
                if isinstance(data, dict):
                    history_list = [data]
                # Nếu dữ liệu đã là list (cấu trúc mới), giữ nguyên
                elif isinstance(data, list):
                    history_list = data
        except (json.JSONDecodeError, ValueError):
            # Nếu file rỗng hoặc lỗi định dạng, khởi tạo danh sách rỗng
            history_list = []

    # Thêm lịch sử mới vào danh sách
    new_history = {
        "schedule": schedule,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    history_list.append(new_history)

    # Lưu lại toàn bộ danh sách lịch sử
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

# Hàm đọc lịch sử từ JSON
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Nếu dữ liệu là một dictionary (cấu trúc cũ), chuyển thành list
                if isinstance(data, dict):
                    return [data]
                # Nếu dữ liệu là list (cấu trúc mới), trả về nguyên
                elif isinstance(data, list):
                    return data
                else:
                    return []  # Nếu dữ liệu không hợp lệ, trả về list rỗng
        except (json.JSONDecodeError, ValueError):
            # Nếu file rỗng hoặc lỗi định dạng, trả về list rỗng
            return []
    return []

# Hàm đọc dữ liệu từ file Excel
def load_from_excel(file):
    xl = pd.ExcelFile(file)
    st.session_state.classroom_data = []
    st.session_state.teacher_data = []
    st.session_state.student_groups = []
    st.session_state.courses = []

    # Đọc sheet "Phòng Học"
    if "Phòng Học" in xl.sheet_names:
        df = pd.read_excel(file, sheet_name="Phòng Học")
        for _, row in df.iterrows():
            if not validate_name(row["Tên phòng học"]):
                st.error(f"Tên phòng học '{row['Tên phòng học']}' chứa ký tự đặc biệt!")
                return False
            st.session_state.classroom_data.append({
                "name": row["Tên phòng học"],
                "capacity": int(row["Sức chứa"]),
                "equipment": row["Thiết bị"].split(","),
                "location": row["Vị trí"]
            })

    # Đọc sheet "Giáo Viên"
    if "Giáo Viên" in xl.sheet_names:
        df = pd.read_excel(file, sheet_name="Giáo Viên")
        for _, row in df.iterrows():
            if not validate_name(row["Tên giáo viên"]):
                st.error(f"Tên giáo viên '{row['Tên giáo viên']}' chứa ký tự đặc biệt!")
                return False
            if not validate_time_format(row["Thời gian rảnh"]):
                st.error(f"Thời gian rảnh '{row['Thời gian rảnh']}' không đúng định dạng!")
                return False
            st.session_state.teacher_data.append({
                "name": row["Tên giáo viên"],
                "available_times": [t.strip() for t in row["Thời gian rảnh"].split(",") if t.strip()]
            })

    # Đọc sheet "Nhóm Sinh Viên"
    if "Nhóm Sinh Viên" in xl.sheet_names:
        df = pd.read_excel(file, sheet_name="Nhóm Sinh Viên")
        for _, row in df.iterrows():
            if not validate_name(row["Tên nhóm"]):
                st.error(f"Tên nhóm '{row['Tên nhóm']}' chứa ký tự đặc biệt!")
                return False
            st.session_state.student_groups.append({
                "name": row["Tên nhóm"],
                "size": int(row["Số sinh viên"])
            })

    # Đọc sheet "Môn Học"
    if "Môn Học" in xl.sheet_names:
        df = pd.read_excel(file, sheet_name="Môn Học")
        for _, row in df.iterrows():
            if not validate_name(row["Tên môn học"]) or not validate_name(row["Giáo viên"]) or not validate_name(row["Nhóm sinh viên"]):
                st.error(f"Tên trong môn học '{row['Tên môn học']}' chứa ký tự đặc biệt!")
                return False
            st.session_state.courses.append({
                "name": row["Tên môn học"],
                "teacher": row["Giáo viên"],
                "group": row["Nhóm sinh viên"],
                "duration": int(row["Thời lượng (số tiết)"]),
                "required_equipment": row["Thiết bị yêu cầu"].split(",")
            })

    st.success("Đã tải dữ liệu từ file Excel!")
    return True

# Hàm khởi tạo session_state nếu chưa có
def initialize_session_state():
    if "classroom_data" not in st.session_state:
        st.session_state.classroom_data = []
    if "teacher_data" not in st.session_state:
        st.session_state.teacher_data = []
    if "student_groups" not in st.session_state:
        st.session_state.student_groups = []
    if "courses" not in st.session_state:
        st.session_state.courses = []

# Hàm xóa dữ liệu trong session_state
def clear_session_state():
    st.session_state.classroom_data = []
    st.session_state.teacher_data = []
    st.session_state.student_groups = []
    st.session_state.courses = []

# Gọi khởi tạo session_state ngay khi ứng dụng chạy
initialize_session_state()

# ============================== GIAO DIỆN STREAMLIT ============================== #
st.title("Lập Lịch Học Tự Động bằng Thuật Toán Di Truyền")

# Sidebar điều hướng
st.sidebar.title("Điều Hướng")
data_choice = st.sidebar.radio("Chọn nguồn dữ liệu", ["Nhập tay", "Tải từ Excel"], key="data_choice")
menu = st.sidebar.radio("Chọn chức năng", ["Nhập Dữ Liệu", "Xem Lịch Học", "Xem Lịch Sử"], key="menu")

# Xử lý tải file Excel
if data_choice == "Tải từ Excel":
    uploaded_file = st.sidebar.file_uploader("Tải file Excel", type=["xlsx"])
    if uploaded_file and st.sidebar.button("Xác nhận tải"):
        clear_session_state()
        if load_from_excel(uploaded_file):
            st.sidebar.success("Dữ liệu đã được tải từ Excel!")
        else:
            st.sidebar.error("Tải dữ liệu thất bại do lỗi định dạng!")

# ============================== HÀM NHẬP DỮ LIỆU ============================== #
def input_data():
    st.header("Nhập Dữ Liệu Đầu Vào")
    if data_choice == "Nhập tay":
        tab1, tab2, tab3, tab4 = st.tabs(["Phòng Học", "Giáo Viên", "Nhóm Sinh Viên", "Môn Học"])
        
        with tab1:
            st.subheader("Thông Tin Phòng Học")
            num_classrooms = st.number_input("Số lượng phòng học", min_value=1, step=1, key="num_classrooms")
            for i in range(num_classrooms):
                with st.expander(f"Phòng học {i+1}", expanded=False):
                    room_name = st.text_input(f"Tên phòng học {i+1}", key=f"room_name_{i}")
                    capacity = st.number_input(f"Sức chứa", min_value=1, step=1, key=f"capacity_{i}")
                    equipment = st.text_input(f"Thiết bị (cách nhau bằng dấu phẩy)", key=f"equip_{i}")
                    location = st.text_input(f"Vị trí (ví dụ: Tòa A Tầng 2)", key=f"location_{i}")
                    if st.button(f"Lưu phòng {i+1}", key=f"save_room_{i}"):
                        if not room_name:
                            st.error("Tên phòng học không được để trống!")
                        elif not validate_name(room_name):
                            st.error("Tên phòng học không được chứa ký tự đặc biệt!")
                        elif not equipment:
                            st.error("Thiết bị không được để trống!")
                        elif not location:
                            st.error("Vị trí không được để trống!")
                        else:
                            st.session_state.classroom_data.append({
                                "name": room_name, "capacity": capacity, "equipment": equipment.split(","), "location": location
                            })
                            st.success(f"Đã lưu phòng {room_name}")
        
        with tab2:
            st.subheader("Thông Tin Giáo Viên")
            num_teachers = st.number_input("Số lượng giáo viên", min_value=1, step=1, key="num_teachers")
            for i in range(num_teachers):
                with st.expander(f"Giáo viên {i+1}", expanded=False):
                    teacher_name = st.text_input(f"Tên giáo viên {i+1}", key=f"teacher_name_{i}")
                    available_times = st.text_area(f"Thời gian rảnh (Thứ 2-7 hoặc Thứ CN-HH:MM-HH:MM, cách nhau dấu phẩy, ví dụ: Thứ 2-13:00-17:00)", key=f"time_{i}")
                    if st.button(f"Lưu giáo viên {i+1}", key=f"save_teacher_{i}"):
                        if not teacher_name:
                            st.error("Tên giáo viên không được để trống!")
                        elif not validate_name(teacher_name):
                            st.error("Tên giáo viên không được chứa ký tự đặc biệt!")
                        elif not available_times:
                            st.error("Thời gian rảnh không được để trống!")
                        elif not validate_time_format(available_times):
                            st.error("Thời gian rảnh không đúng định dạng! Ví dụ: Thứ 2-13:00-17:00")
                        else:
                            st.session_state.teacher_data.append({
                                "name": teacher_name, "available_times": [t.strip() for t in available_times.split(",") if t.strip()]
                            })
                            st.success(f"Đã lưu giáo viên {teacher_name}")
        
        with tab3:
            st.subheader("Thông Tin Nhóm Sinh Viên")
            num_groups = st.number_input("Số lượng nhóm sinh viên", min_value=1, step=1, key="num_groups")
            for i in range(num_groups):
                with st.expander(f"Nhóm sinh viên {i+1}", expanded=False):
                    group_name = st.text_input(f"Tên nhóm {i+1}", key=f"group_name_{i}")
                    student_count = st.number_input(f"Số sinh viên", min_value=1, step=1, key=f"size_{i}")
                    if st.button(f"Lưu nhóm {i+1}", key=f"save_group_{i}"):
                        if not group_name:
                            st.error("Tên nhóm không được để trống!")
                        elif not validate_name(group_name):
                            st.error("Tên nhóm không được chứa ký tự đặc biệt!")
                        else:
                            st.session_state.student_groups.append({
                                "name": group_name, "size": student_count
                            })
                            st.success(f"Đã lưu nhóm {group_name}")
        
        with tab4:
            st.subheader("Thông Tin Môn Học")
            num_courses = st.number_input("Số lượng môn học", min_value=1, step=1, key="num_courses")
            for i in range(num_courses):
                with st.expander(f"Môn học {i+1}", expanded=False):
                    course_name = st.text_input(f"Tên môn học {i+1}", key=f"course_name_{i}")
                    teacher = st.text_input(f"Giáo viên", key=f"course_teacher_{i}")
                    group = st.text_input(f"Nhóm sinh viên", key=f"course_group_{i}")
                    duration = st.number_input(f"Thời lượng (số tiết)", min_value=1, step=1, key=f"duration_{i}")
                    required_equipment = st.text_input(f"Thiết bị yêu cầu (cách nhau bằng dấu phẩy)", key=f"req_equip_{i}")
                    if st.button(f"Lưu môn {i+1}", key=f"save_course_{i}"):
                        if not course_name:
                            st.error("Tên môn học không được để trống!")
                        elif not validate_name(course_name):
                            st.error("Tên môn học không được chứa ký tự đặc biệt!")
                        elif not teacher:
                            st.error("Giáo viên không được để trống!")
                        elif not validate_name(teacher):
                            st.error("Tên giáo viên không được chứa ký tự đặc biệt!")
                        elif not group:
                            st.error("Nhóm sinh viên không được để trống!")
                        elif not validate_name(group):
                            st.error("Tên nhóm sinh viên không được chứa ký tự đặc biệt!")
                        elif not required_equipment:
                            st.error("Thiết bị yêu cầu không được để trống!")
                        else:
                            st.session_state.courses.append({
                                "name": course_name, "teacher": teacher, "group": group, 
                                "duration": duration, "required_equipment": required_equipment.split(",")
                            })
                            st.success(f"Đã lưu môn {course_name}")

    if st.button("Xóa Dữ Liệu", key="clear_data"):
        clear_session_state()
        st.success("Đã xóa dữ liệu hiện tại!")

# ============================== THUẬT TOÁN DI TRUYỀN ============================== #
def generate_schedule():
    if not all([st.session_state.classroom_data, st.session_state.teacher_data, st.session_state.courses]):
        return []
    
    schedule = []
    used_rooms_times = {}
    
    for course in st.session_state.courses:
        teacher = next((t for t in st.session_state.teacher_data if t['name'] == course['teacher']), None)
        group = next((g for g in st.session_state.student_groups if g['name'] == course['group']), None)
        
        if not teacher or not group:
            continue
        
        required_minutes = calculate_duration_minutes(course['duration'])
        
        valid_rooms = [
            room for room in st.session_state.classroom_data
            if room['capacity'] >= group['size'] and 
               all(eq in room['equipment'] for eq in course['required_equipment'])
        ]
        
        if not valid_rooms:
            continue
        
        for time in teacher['available_times']:
            if not is_time_slot_sufficient(time, required_minutes):
                continue
            
            available_rooms = [
                room for room in valid_rooms 
                if time not in used_rooms_times.get(room['name'], [])
            ]
            if available_rooms:
                room = random.choice(available_rooms)
                schedule.append({
                    "Môn học": course["name"], "Phòng học": room["name"], 
                    "Giáo viên": course["teacher"], "Nhóm sinh viên": course["group"], 
                    "Thời gian": time, "Location": room["location"]
                })
                used_rooms_times.setdefault(room['name'], []).append(time)
                break
        else:
            continue
    
    return schedule

def fitness_function(schedule):
    if not schedule:
        return -float('inf')
    
    score = 0
    used_times_teacher = {}
    used_times_group = {}
    used_rooms_times = {}
    teacher_locations = {}
    group_locations = {}
    
    for entry in schedule:
        teacher = entry['Giáo viên']
        group = entry['Nhóm sinh viên']
        room = entry['Phòng học']
        time = entry['Thời gian']
        
        if time in used_rooms_times.get(room, []):
            return -float('inf')
        if time in used_times_teacher.get(teacher, []):
            return -float('inf')
        if time in used_times_group.get(group, []):
            return -float('inf')
        
        used_rooms_times.setdefault(room, []).append(time)
        used_times_teacher.setdefault(teacher, []).append(time)
        used_times_group.setdefault(group, []).append(time)
        
        teacher_locations.setdefault(teacher, []).append((time, entry['Location']))
        group_locations.setdefault(group, []).append((time, entry['Location']))
    
    score += len(schedule) * 100
    
    for locations in [teacher_locations, group_locations]:
        for entity, time_locs in locations.items():
            sorted_locs = sorted(time_locs, key=lambda x: x[0])
            for i in range(1, len(sorted_locs)):
                if sorted_locs[i][1] != sorted_locs[i-1][1]:
                    score -= 10
    
    for entry in schedule:
        room = next(r for r in st.session_state.classroom_data if r['name'] == entry['Phòng học'])
        group = next(g for g in st.session_state.student_groups if g['name'] == entry['Nhóm sinh viên'])
        excess_capacity = room['capacity'] - group['size']
        if excess_capacity > 20:
            score -= excess_capacity // 10
    
    return score

def crossover(parent1, parent2):
    crossover_point = len(parent1) // 2
    child = parent1[:crossover_point] + parent2[crossover_point:]
    return child

def mutate(schedule):
    if not schedule:
        return schedule
    idx = random.randint(0, len(schedule) - 1)
    course = next(c for c in st.session_state.courses if c['name'] == schedule[idx]['Môn học'])
    teacher = next(t for t in st.session_state.teacher_data if t['name'] == course['teacher'])
    group = next(g for g in st.session_state.student_groups if g['name'] == course['group'])
    
    required_minutes = calculate_duration_minutes(course['duration'])
    valid_rooms = [
        r for r in st.session_state.classroom_data
        if r['capacity'] >= group['size'] and all(eq in r['equipment'] for eq in course['required_equipment'])
    ]
    if valid_rooms:
        for time in teacher['available_times']:
            if is_time_slot_sufficient(time, required_minutes):
                room = random.choice(valid_rooms)
                schedule[idx] = {
                    "Môn học": course["name"], "Phòng học": room["name"], 
                    "Giáo viên": course["teacher"], "Nhóm sinh viên": course["group"], 
                    "Thời gian": time, "Location": room["location"]
                }
                break
    return schedule

def genetic_algorithm():
    population_size = 100
    generations = 500
    mutation_rate = 0.1
    
    population = [generate_schedule() for _ in range(population_size)]
    if not any(population):
        return []
    
    for _ in range(generations):
        population = sorted(population, key=fitness_function, reverse=True)
        if fitness_function(population[0]) == -float('inf'):
            return []
        new_population = population[:10]
        while len(new_population) < population_size:
            parent1, parent2 = random.sample(population[:50], 2)
            child = crossover(parent1, parent2)
            if random.random() < mutation_rate:
                child = mutate(child)
            new_population.append(child)
        population = new_population
    return population[0]

# ============================== CHẠY ỨNG DỤNG ============================== #
if menu == "Nhập Dữ Liệu":
    input_data()
elif menu == "Xem Lịch Học":
    st.header("Lịch Học Tối Ưu")
    # Kiểm tra xem các thuộc tính có tồn tại và có dữ liệu không
    has_data = (
        hasattr(st.session_state, "courses") and st.session_state.courses and
        hasattr(st.session_state, "classroom_data") and st.session_state.classroom_data and
        hasattr(st.session_state, "teacher_data") and st.session_state.teacher_data
    )
    if not has_data:
        st.warning("Vui lòng nhập dữ liệu (phòng học, giáo viên, môn học) trước khi tạo lịch!")
    elif st.button("Tạo Lịch Học", key="generate_schedule"):
        with st.spinner("Đang tạo lịch học tối ưu..."):
            best_schedule = genetic_algorithm()
            if not best_schedule:
                st.error("Không thể tạo lịch học. Vui lòng kiểm tra dữ liệu đầu vào!")
            else:
                save_history(best_schedule)
                st.subheader("Kết Quả Lịch Học")
                df_schedule = pd.DataFrame(best_schedule)
                styled_df = df_schedule.style.set_properties(**{
                    'background-color': '#ffffff',
                    'color': '#333333',
                    'border-color': '#cccccc',
                    'text-align': 'center',
                    'font-size': '14px',
                    'padding': '8px'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]}
                ])
                st.dataframe(styled_df, height=300)
                # Sửa phần tải xuống: Sử dụng dấu chấm phẩy làm dấu phân tách
                csv_buffer = df_schedule.to_csv(index=False, encoding='utf-8-sig', sep=';').encode('utf-8-sig')
                st.download_button(
                    label="Tải xuống lịch học (CSV)",
                    data=csv_buffer,
                    file_name="lich_hoc.csv",
                    mime="text/csv"
                )
elif menu == "Xem Lịch Sử":
    st.header("Lịch Sử Lịch Học")
    history_list = load_history()

    if history_list:
        # Thêm giao diện chọn ngày
        st.subheader("Chọn ngày để xem lịch sử")
        selected_date = st.date_input("Chọn ngày", value=datetime.today())

        # Chuyển đổi ngày được chọn thành định dạng "YYYY-MM-DD"
        selected_date_str = selected_date.strftime("%Y-%m-%d")

        # Lọc lịch sử theo ngày được chọn
        filtered_histories = [
            history for history in history_list
            if history["timestamp"].startswith(selected_date_str)
        ]

        if filtered_histories:
            # Hiển thị tất cả lịch sử trong ngày được chọn
            for idx, history in enumerate(filtered_histories):
                st.write(f"**Lịch sử {idx + 1} - Thời gian tạo: {history['timestamp']}**")
                df_history = pd.DataFrame(history["schedule"])
                styled_df = df_history.style.set_properties(**{
                    'background-color': '#ffffff',
                    'color': '#333333',
                    'border-color': '#cccccc',
                    'text-align': 'center',
                    'font-size': '14px',
                    'padding': '8px'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]}
                ])
                st.dataframe(styled_df, height=300)
                # Tải xuống lịch sử
                csv_buffer = df_history.to_csv(index=False, encoding='utf-8-sig', sep=';').encode('utf-8-sig')
                st.download_button(
                    label=f"Tải xuống lịch sử {idx + 1} (CSV)",
                    data=csv_buffer,
                    file_name=f"lich_su_{history['timestamp'].replace(':', '-')}.csv",
                    mime="text/csv"
                )
        else:
            st.info(f"Không có lịch sử lịch học nào cho ngày {selected_date_str}!")
    else:
        st.info("Chưa có lịch sử lịch học nào!")