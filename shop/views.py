from django.shortcuts import render, get_object_or_404

from cart.forms import CartAddProductForm
from .models import Category, Product, Comment
from .forms import CommentForm, SearchForm
from .recommender import Recommender
from django.views.decorators.http import require_POST
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
import redis
from django.conf import settings
from icecream import ic

# Create your views here.

# соединить с redis
red = redis.Redis(host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB)



def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        language = request.LANGUAGE_CODE
        category = get_object_or_404(Category,
                                     translations__language_code=language,
                                     translations__slug=category_slug)

        products = products.filter(category=category)
    return render(request, 'shop/product/list.html', {'category': category,
                                                      'categories': categories,
                                                      'products': products
                                                      })


def product_detail(request, id, slug):
    language = request.LANGUAGE_CODE
    product = get_object_or_404(Product,
                                translations__language_code=language,
                                translations__slug=slug,
                                id=id, available=True)
    # Список активных комментариев к этому посту
    comments = product.comments.filter(active=True)
    # Форма для комментирования пользователями
    form = CommentForm()
    cart_product_form = CartAddProductForm()
    r = Recommender()
    recommended_products = r.suggest_products_for([product], 4)
    # увеличить общее число просмотров продукта на 1
    total_views = red.incr(f'product:{product.id}:views')
    # увеличить рейтинг продукта на 1
    red.zincrby('product_ranking', 1, product.id)
    video = product.url
    return render(request, 'shop/product/detail.html', {'product': product,
                                                        'cart_product_form': cart_product_form,
                                                        'recommended_products': recommended_products,
                                                        'comments': comments,
                                                        'form': form, 'total_views': total_views,
                                                        'video': video})


@require_POST
def product_comment(request, id, slug):
    product = get_object_or_404(Product, id=id, available=True, translations__slug=slug)
    comment = None
    # Комментарий был отправлен
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить продукт комментарию
        comment.merchandise = product
        # Сохранить комментарий
        comment.save()
    return render(request, 'shop/product/comment.html', {'product': product,
                                                         'form': form,
                                                         'comment': comment})


def product_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # search_vector = SearchVector('translations__name', weight='A', config='english, uzbek, russian') + \
            #                 SearchVector('translations__description', weight='B')
            # search_query = SearchQuery(query)
            results = Product.objects.filter(available=True).annotate(
                similarity=TrigramSimilarity('translations__name', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
    return render(request, 'shop/product/search.html', {'form': form, 'query': query, 'results': results})


def product_ranking(request):
    # получить словарь рейтинга продуктов
    product_ranking = red.zrange('product_ranking', 0, -1, desc=True)[:10]
    product_ranking_ids = [int(id) for id in product_ranking]
    # получить наиболее просматриваемые продукты
    most_viewed = list(Product.objects.filter(id__in=product_ranking_ids))
    most_viewed.sort(key=lambda x: product_ranking_ids.index(x.id))
    return render(request, 'shop/product/ranking.html', {'most_viewed': most_viewed})
