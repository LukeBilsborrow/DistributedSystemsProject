from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

User = get_user_model()


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # read the next parameter from the query string
            next_param = request.GET.get("next")
            if next_param:
                return redirect(next_param)
            return redirect("/profile/")
        else:
            error_message = "Invalid username or password."
            return render(request, "login.html", {"error_message": error_message})
    else:
        return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = User.objects.create_user(username=username, password=password)
        user.save()

        user = authenticate(request, username=username, password=password)

        next_param = request.GET.get("next")
        if next_param:
            return redirect(next_param)

        return redirect("/")
    else:
        return render(request, "register.html")
