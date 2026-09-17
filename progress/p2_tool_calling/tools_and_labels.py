# -*- coding: utf-8 -*-
# 重新逐句核對過的正確標籤（第一版把 82-102 幾乎全部誤標成 dev_tool_op，已修正）
TOOLS = [
    "open_app", "close_window", "set_volume", "get_datetime", "get_weather",
    "adjust_brightness", "take_screenshot", "clipboard_op", "file_op",
    "window_op", "power_op", "network_toggle", "media_control",
    "calendar_op", "reminder_op", "print_or_scan", "photo_edit",
    "text_input_op", "text_to_speech_op", "speech_to_text_op", "translate",
    "get_exchange_rate", "alarm_op", "calculator", "cloud_file_op",
    "email_op", "video_call_op", "record_screen", "system_maintenance",
    "task_scheduler_op", "startup_program_op", "driver_op", "dev_tool_op",
    "git_op", "summarize_doc",
]

LABELS = {
1:"open_app",2:"open_app",3:"close_window",4:"set_volume",5:"set_volume",
6:"get_datetime",7:"get_datetime",8:"get_weather",9:"open_app",10:"file_op",
11:"adjust_brightness",12:"adjust_brightness",13:"take_screenshot",14:"clipboard_op",15:"clipboard_op",
16:"file_op",17:"file_op",18:"file_op",19:"window_op",20:"window_op",
21:"window_op",22:"window_op",23:"power_op",24:"power_op",25:"power_op",
26:"open_app",27:"open_app",28:"open_app",29:"network_toggle",30:"network_toggle",
31:"network_toggle",32:"network_toggle",33:"network_toggle",34:"media_control",35:"media_control",
36:"media_control",37:"media_control",38:"media_control",39:"open_app",40:"calendar_op",
41:"reminder_op",42:"reminder_op",43:"file_op",44:"print_or_scan",45:"print_or_scan",
46:"photo_edit",47:"photo_edit",48:"photo_edit",49:"photo_edit",50:"open_app",
51:"text_input_op",52:"text_to_speech_op",53:"speech_to_text_op",54:"translate",55:"translate",
56:"get_exchange_rate",57:"get_weather",58:"alarm_op",59:"alarm_op",60:"alarm_op",
61:"calculator",62:"cloud_file_op",63:"cloud_file_op",64:"cloud_file_op",65:"email_op",
66:"email_op",67:"email_op",68:"email_op",69:"video_call_op",70:"record_screen",
71:"record_screen",72:"file_op",73:"open_app",74:"open_app",75:"media_control",
76:"set_volume",77:"system_maintenance",78:"system_maintenance",79:"system_maintenance",80:"system_maintenance",
81:"system_maintenance",82:"open_app",83:"task_scheduler_op",84:"startup_program_op",85:"startup_program_op",
86:"open_app",87:"driver_op",88:"driver_op",89:"open_app",90:"dev_tool_op",
91:"dev_tool_op",92:"dev_tool_op",93:"open_app",94:"file_op",95:"git_op",
96:"git_op",97:"git_op",98:"git_op",99:"git_op",100:"git_op",
101:"git_op",102:"git_op",103:"summarize_doc",
}

# 已知天生模糊、容許模型給出「合理但跟標籤不同」答案的題號（評分時額外註記，不算硬性錯誤）
AMBIGUOUS = {2, 39, 51, 61, 69, 72, 73, 74, 82, 86, 89, 93}
