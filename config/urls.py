"""
URL configuration for src project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from src.api.block_reasons.views import get_block_reasons
from src.api.descisions.views import accept, decline
from src.api.queue.views import get_next_product
urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/product-moderation/get-next/', get_next_product),
    path('api/v1/products/<uuid:product_id>/approve/', accept),
    path('api/v1/products/<uuid:product_id>/decline/', decline),
    path('api/v1/product-blocking-resons/', get_block_reasons)
]
