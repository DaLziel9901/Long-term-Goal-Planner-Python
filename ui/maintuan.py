import tkinter as tk

window = tk.Tk()

window.title("Ứng dụng lịch dài hạn")
window.geometry("800x600")

firstSay=tk.Label(text="PYTHON_N09")
firstSay.pack(pady=20)

#thanh chứa 2 button

taskbar = tk.Frame(window,bg="lightblue",width=200,height=200)
taskbar.pack(fill="x",padx=10,pady=20)  

#khung dưới 1 (khung kế hoạch)
under_frame_1 = tk.Frame(window)
under_frame_1.pack(fill="x",padx=10)

#khung dưới 2 (khung thống kê)
under_frame_2 = tk.Frame(window,bg="red")
under_frame_2.pack(fill="x",padx=10)

#khung dưới 3 (khung lịch tuần)
under_frame_3 = tk.Frame(window,bg="blue")
under_frame_3.pack(fill="x",padx=10)

#khung project
project_frame = tk.Frame(under_frame_1,bg="lightgreen",width=200,height=300)
project_frame.pack(side="left")
project_frame.pack_propagate(False)

#thanh chứa nội dung 
contentbar = tk.Frame(under_frame_1,bg="blue",width=700,height=300)
contentbar.pack(side="left")
contentbar.pack_propagate(False)

#Label in taskbar
title1 = tk.Label(taskbar,text="Ứng dụng lịch",bg="lightblue")
title1.pack(side="left",padx=10,pady=10)

#Tiêu đề khung project
title2 = tk.Label(project_frame,text="Dự án",bg="white")
title2.pack(pady=10)

# #khung 1 
# frame1= tk.Frame(contentbar,bg="green",width=300,height=300)

# text1 = tk.Label(frame1,text="Nội dung số 1")
# text1.pack(padx=20,pady=20)

# #frame2
# frame2 = tk.Frame(contentbar,bg="purple",width=300,height=300)

# text2=tk.Label(frame2,text="Nội dung số 2")
# text2.pack(padx=20,pady=20)

# #frame3
# frame3 = tk.Frame(contentbar,bg="red",width=300,height=300)

# text3=tk.Label(frame3,text="Nội dung số 3")
# text3.pack(padx=20,pady=20)

#ham khi bam nut 
def show_frame1() :
    under_frame_2.pack_forget()
    under_frame_3.pack_forget()
    under_frame_1.pack()
def show_frame2():
    under_frame_1.pack_forget()
    under_frame_3.pack_forget()
    under_frame_2.pack()
def show_frame3():
    under_frame_2.pack_forget()
    under_frame_1.pack_forget()
    under_frame_3.pack()

#nut trong thanh taskbar

button1 = tk.Button(taskbar,text="Kế hoạch",command=show_frame1)
button1.pack(side="left",padx=10,pady=10)

button2 = tk.Button(taskbar,text="Thống kê",command=show_frame2)
button2.pack(side="left",padx=10,pady=10)

button3 = tk.Button(taskbar,text="Lịch tuần",command=show_frame3)
button3.pack(side="left",padx=10,pady=10)

#nút Thêm dự án 
button_add=tk.Button(project_frame,text="Thêm dự án")
button_add.pack(fill="x",padx=10)

window.mainloop()