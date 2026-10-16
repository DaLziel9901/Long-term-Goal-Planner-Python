import tkinter as tk

window = tk.Tk()

window.title("Ứng dụng lịch dài hạn")
window.geometry("800x600")

firstSay=tk.Label(text="Chuyển đổi giữa 2 khung")
firstSay.pack(pady=20)

#thanh chứa 2 button

taskbar = tk.Frame(window,bg="lightblue",width=200,height=200)
taskbar.pack(fill="y",padx=20,pady=20)

#thanh chứa nội dung 

contentbar = tk.Frame(window,bg="blue",width=300,height=300)
contentbar.pack()
contentbar.pack_propagate(False)
#khung 1 

frame1= tk.Frame(contentbar,bg="green",width=300,height=300)

text1 = tk.Label(frame1,text="Nội dung số 1")
text1.pack(padx=20,pady=20)

#frame2
frame2 = tk.Frame(contentbar,bg="purple",width=300,height=300)

text2=tk.Label(frame2,text="Nội dung số 2")
text2.pack(padx=20,pady=20)

#ham khi bam nut 
def show_frame1() :
    frame2.pack_forget()
    frame1.pack(fill="both",expand=True)
def show_frame2():
    frame1.pack_forget()
    frame2.pack(fill="both",expand=True)

#nut

button1 = tk.Button(taskbar,text="FIRST",command=show_frame1)
button1.pack(side="left",padx=10,pady=10)

button2 = tk.Button(taskbar,text="SECOND",command=show_frame2)
button2.pack(side="left",padx=10,pady=10)

window.mainloop()