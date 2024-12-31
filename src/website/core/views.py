from django.http import HttpResponse


from rest_framework.decorators import api_view

# import django class view for APIView


from django.template import loader


@api_view(["GET"])
def index_view(request):
    template = loader.get_template("index.html")

    context = {}
    return HttpResponse(template.render(context, request))
