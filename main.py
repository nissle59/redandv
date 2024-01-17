import requests
import csv
from pathlib import Path


class Redan():
    token = 'zAnepAR9'
    base_url = 'https://opt.redandv.ru/export/api/json'
    cat_url = f'{base_url}/category/?key={token}'
    prod_url = f'{base_url}/product/?op=stock&key={token}'
    img_url = f'{base_url}/image/?op=item&key={token}&id='

    categories = {}
    cat_to_load = []
    state = -1
    products = []

    def __init__(self):
        self.state = self.init_categories()

    def init_categories(self):
        r = requests.get(self.cat_url)
        try:
            js = r.json()['categories']
            cat_filter = Path("cat_filter.csv")
            self.cat_to_load = []
            if not (cat_filter.is_file()):
                with open("cat_filter.csv", mode="w", encoding='utf-8-sig') as w_file:
                    file_writer = csv.writer(w_file, delimiter=";", lineterminator="\r")
                    file_writer.writerow(["id", "Category","Parent", "Get"])
                    for item in js:
                        file_writer.writerow([item['id'], item['name'], item.get('parent_id',''), "1"])
                        self.cat_to_load.append(item['id'])
                return 1
            else:
                with open("cat_filter.csv", mode="r", encoding='utf-8-sig') as r_file:
                    file_reader = csv.DictReader(r_file, delimiter=";")
                    for row in file_reader:
                        if row['Get'] == '1':
                            self.cat_to_load.append(row['id'])
                return 0

        except:
            return -1

    def get_products(self):
        r = requests.get(self.prod_url)
        try:
            js = r.json()['stock']
            for prod in js:
                if prod.get('category_id') in self.cat_to_load:
                    self.products.append(prod)
            return 1
        except:
            return -1

    def make_csvs(self,msk = 'msk.csv', chab = 'chab.csv'):
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
            'Товар в пути'
        ]
        msk_writer = csv.DictWriter(mskf, delimiter = ";",lineterminator="\r", fieldnames=names)
        chab_writer = csv.DictWriter(chabf, delimiter=";", lineterminator="\r", fieldnames=names)
        msk_writer.writeheader()
        chab_writer.writeheader()
        for product in self.products:
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

            msk_writer.writerow({
                'Артикул(1)':product.get('sku'),
                'Наименование(2)':product.get('name'),
                'Бренд(3)':product.get('brand'),
                'Склад':'Москва',
                'Количество(5)':msk_count,
                'Цена(6)':price,
                'Распродажа':'',
                'Мин. заказ':'1',
                'Срок поставки (Рабочие дни)':'0',
                'Уцененный товар':'',
                'Авиадоставка':'',
                'Товар в пути':''
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
                'Товар в пути': ''
            })
        mskf.close()
        chabf.close()

if __name__ == '__main__':
    rdv = Redan()
    if rdv.state > -1:
        if rdv.get_products()>0:
            rdv.make_csvs()