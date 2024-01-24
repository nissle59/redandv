import json

import requests
import csv
from pathlib import Path
import threading

cats_handler = open('categories.txt', 'w')


def pretty(dd, key_f, indent=0):
    global cats_handler
    if isinstance(dd, list):
        for d in dd:
            for key, value in d.items():
                # print('\t' * indent + str(key))
                if isinstance(value, dict) or isinstance(value, list):
                    pretty(value, key_f, indent + 1)
                else:
                    if key == key_f:
                        cats_handler.write('\t' * (indent + 1) + f'({d.get("id")}) ' + str(value) + '\n')
    else:
        d = dd
        for key, value in d.items():
            # print('\t' * indent + str(key))
            if isinstance(value, dict) or isinstance(value, list):
                pretty(value, key_f, indent + 1)
            else:
                if key == key_f:
                    cats_handler.write('\t' * (indent + 1) + f'({d.get("id")}) ' + str(value) + '\n')


def create_tree(data):
    tree = {}
    nodes = {}
    for i in data:
        id = i['id']
        nodes[id] = i

    forest = []
    for i in data:
        id = i['id']
        parent_id = i.get('parent_id', None)
        node = nodes[id]

        # either make the node a new tree or link it to its parent
        if (id == parent_id) or (parent_id == None):
            # start a new tree in the forest
            forest.append(node)
            forest.sort(key=lambda x: (x['id']))
        else:
            # add new_node as child to parent
            parent = nodes[parent_id]
            if not 'children' in parent:
                # ensure parent has a 'children' field
                parent['children'] = []
            children = parent['children']
            children.append(node)
            children.sort(key=lambda x: (x['id']))
    return forest


def find_in_nested_dict(d: dict, value, key='id'):
    if isinstance(d, list):
        for dd in d:
            if key in dd:
                if dd[key] == value:
                    return dd
            for k, v in dd.items():
                if isinstance(v, dict):
                    result = find_in_nested_dict(v, value)
                    if result is not None:
                        return result
                elif isinstance(v, list):
                    for i in v:
                        result = find_in_nested_dict(v, value)
                        if result is not None:
                            return result
    else:
        if key in d:
            if d[key] == value:
                return d
        for k, v in d.items():
            if isinstance(v, dict):
                result = find_in_nested_dict(v, value)
                if result is not None:
                    return result
            elif isinstance(v, list):
                for i in v:
                    result = find_in_nested_dict(v, value)
                    if result is not None:
                        return result
    return None


class Redan():
    token = 'zAnepAR9'
    base_url = 'https://opt.redandv.ru/export/api/json'
    cat_url = f'{base_url}/category/?key={token}'
    prod_url = f'{base_url}/product/?op=stock&key={token}'
    img_url = f'{base_url}/image/?op=item&key={token}&id='
    base_img_path = 'images/'

    categories = {}
    cat_to_load = []
    state = -1
    products = []
    ctl = []

    def __init__(self):
        self.state = self.init_categories()

    def collect_cat_ids(self, root_cats: list):
        def rotate(cats):
            if isinstance(cats, list):
                for cat in cats:
                    children = cat.get('children', None)
                    if children:
                        self.ctl.append(cat.get('id', ''))
                        rotate(children)
                    else:
                        self.ctl.append(cat.get('id', ''))
            else:
                cat = cats
                children = cat.get('children', None)
                if children:
                    self.ctl.append(cat.get('id', ''))
                    rotate(children)
                else:
                    self.ctl.append(cat.get('id', ''))

        self.ctl = []
        rotate(root_cats)
        print(f'{len(self.ctl)} categories added')

    def init_categories(self):
        r = requests.get(self.cat_url)
        try:
            js = r.json()['categories']
            self.cat_to_load = []
            self.js_cats = create_tree(js)
            pretty(self.js_cats, 'name')
            cats_handler.close()
            self.cat_to_load = []
            with open('categories_to_parse.txt', 'r') as f:
                input_cats = f.read().split('\n')
            for i in input_cats:
                self.cat_to_load.append(find_in_nested_dict(self.js_cats, i))
            self.collect_cat_ids(self.cat_to_load)
            return 1

        except Exception as e:
            print(e)
            return -1

    def get_products(self):
        r = requests.get(self.prod_url)
        try:
            js = r.json()['stock']
            for prod in js:
                if prod.get('category_id') in self.ctl:
                    self.products.append(prod)
            return 1
        except:
            return -1

    def check_img(self,url):
        try:
            r = requests.get(url)
            b = r.content
            try:
                err = r.json()['error']
                print(f'for {product.get("id")} : {err}')
                img = ''
                return img
            except:
                pass
            # print(b)
            if len(b) > 0:
                if b[:6] != b'<html>':
                    print(f'Load image for {product["id"]}')
                    img = url
        except Exception as e:
            img = ''
        return url

    def make_csvs(self, msk='msk.csv', chab='chab.csv'):
        mskf = open(msk, mode="w", encoding='utf-8-sig')
        chabf = open(chab, mode="w", encoding='utf-8-sig')
        names = [
            'Артикул(1)',
            'Наименование(2)',
            'Бренд(3)',
            'Склад',
            'Количество(5)',
            'Цена(6)',
            'Распродажа',
            'Мин. заказ',
            'Срок поставки (Рабочие дни)',
            'Уцененный товар',
            'Авиадоставка',
            'Товар в пути',
            'Изображение'
        ]
        msk_writer = csv.DictWriter(mskf, delimiter=";", lineterminator="\r", fieldnames=names)
        chab_writer = csv.DictWriter(chabf, delimiter=";", lineterminator="\r", fieldnames=names)
        msk_writer.writeheader()
        chab_writer.writeheader()
        current = 0
        total = len(self.products)
        for product in self.products:
            current += 1
            print(f'Processing {current} product of {total}...')
            msk_count = '0.000'
            chab_count = '0.000'

            try:
                for stock in product.get('stocks'):
                    if stock.get('id') == 1:
                        chab_count = stock.get('count')
                    elif stock.get('id') == 3:
                        msk_count = stock.get('count')
            except:
                msk_count = '0.000'
                chab_count = '0.000'

            price = '0'

            for pr in product.get('prices'):
                if pr.get('type') == 'purchase':
                    price = pr['price']

            img = self.check_img(f'{self.base_url}/image/?op=item&id={product.get("id")}&key={self.token}')

            msk_writer.writerow({
                'Артикул(1)': product.get('sku'),
                'Наименование(2)': product.get('name'),
                'Бренд(3)': product.get('brand'),
                'Склад': 'Москва',
                'Количество(5)': msk_count,
                'Цена(6)': price,
                'Распродажа': '',
                'Мин. заказ': '1',
                'Срок поставки (Рабочие дни)': '0',
                'Уцененный товар': '',
                'Авиадоставка': '',
                'Товар в пути': '',
                'Изображение':img
            })
            chab_writer.writerow({
                'Артикул(1)': product.get('sku'),
                'Наименование(2)': product.get('name'),
                'Бренд(3)': product.get('brand'),
                'Склад': 'Хабаровск',
                'Количество(5)': chab_count,
                'Цена(6)': price,
                'Распродажа': '',
                'Мин. заказ': '1',
                'Срок поставки (Рабочие дни)': '0',
                'Уцененный товар': '',
                'Авиадоставка': '',
                'Товар в пути': '',
                'Изображение':img
            })
        mskf.close()
        chabf.close()

    def get_images(self):
        for product in self.products:
            if product.get('category_id') in self.ctl:
                try:
                    r = requests.get(f'{self.base_url}/image/?op=item&id={product.get("id")}&key={self.token}')
                    b = r.content
                    try:
                        err = r.json()['error']
                        print(f'for {product.get("id")} : {err}')
                        continue
                    except:
                        pass
                    # print(b)
                    if len(b) > 0:
                        if b[:6] != b'<html>':
                            print(f'Load image for {product["id"]}')
                            with open(self.base_img_path + product.get('sku') + '@' + product.get('id') + '.jpg',
                                      'wb') as f:
                                f.write(b)
                except Exception as e:
                    print(e)


if __name__ == '__main__':
    # img_path = Path('images')
    # img_path.mkdir(exist_ok=True)
    rdv = Redan()
    if rdv.state > -1:
        if rdv.get_products() > 0:
            skulist = []
            for product in rdv.products:
                skulist.append(product.get('sku') + '@' + product.get('id'))
            newlist = list(set(skulist))
            print(f'{len(skulist)} -> {len(newlist)}')
            rdv.make_csvs()
            # rdv.get_images()
