class Product:
    def __init__(self, product_id: int, name: str, price: float):
        self.product_id = product_id
        self.name = name
        self.price = price


class Order:
    def __init__(self, order_id: int, customer: str):
        self.id = order_id                                   # fix B3: atribut id
        self.customer = customer
        self.status = "pending"                              # fix B4: sumber nilai status
        self.items: list[dict[str, object]] = []             # fix B1: anotasi tipe
        self.total = 0.0

    def add_item(self, product: Product, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self.items.append({
            "product": product,
            "quantity": quantity
        })
        self.total += product.price * quantity

    def apply_discount(self, percentage: float) -> float:
        if percentage < 0 or percentage > 100:
            raise ValueError("Invalid discount")
        discount = self.total * percentage / 100
        return self.total - discount

    def calculate_tax(self, tax_rate: float) -> float:
        tax = self.total * tax_rate
        return tax


class OrderService:
    def __init__(self):
        self.orders: list[Order] = []                        # fix B3: tipe elemen diketahui

    def create_order(self, customer: str) -> Order:
        order = Order(len(self.orders) + 1, customer)        # fix B3: beri id
        self.orders.append(order)
        return order

    def process_order(self, order: Order, discount: float) -> float:
        if order.total > 100000:
            final_price = order.apply_discount(discount)
        else:
            final_price = order.total
        tax = order.calculate_tax(0.11)                      # fix B2: float, bukan str
        return final_price + tax

    def find_order(self, order_id: int) -> Order | None:
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def generate_report(self):
        report = []
        for order in self.orders:
            customer_name = order.customer
            total_price = order.total
            report.append({
                "customer": customer_name,
                "total": total_price,
                "status": order.status                       # fix B4: ambil dari objek
            })
        return report


def calculate_bulk_price(items: list[tuple[Product, int]], discount: float) -> float:
    total = 0.0                                              # fix B6: float sejak awal
    for product, quantity in items:                          # fix B5: quantity dari pasangan, bukan Product
        total += product.price * quantity
    if discount > 0:
        total = total - discount
    return total                                             # fix B7: kembalikan float, bukan str


def main():
    service = OrderService()
    product1 = Product(101, "Laptop", 7500000)
    product2 = Product(102, "Mouse", 150000)
    order = service.create_order("Customer A")
    order.add_item(product1, 1)
    order.add_item(product2, 2)
    final_price = service.process_order(order, 10)
    print("Final Price:", final_price)
    report = service.generate_report()
    print(report)


if __name__ == "__main__":
    main()