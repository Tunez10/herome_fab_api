from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_products(self):
        self.client.get("/api/products/products/")

    @task
    def get_categories(self):
        self.client.get("/api/products/categories/")
