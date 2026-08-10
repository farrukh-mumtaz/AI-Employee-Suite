import time
import concurrent.futures
import requests

# Simple load test: sends multiple concurrent requests to key endpoints
# and measures response times, to check backend behavior under load.

BASE_URL = "http://127.0.0.1:8000"

def hit_health():
    start = time.time()
    response = requests.get(f"{BASE_URL}/health")
    return response.status_code, time.time() - start

def run_load_test(num_requests=50):
    print(f"Sending {num_requests} concurrent requests to /health...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda _: hit_health(), range(num_requests)))

    times = [r[1] for r in results]
    success_count = sum(1 for r in results if r[0] == 200)

    print(f"Successful requests: {success_count}/{num_requests}")
    print(f"Average response time: {sum(times)/len(times):.4f} seconds")
    print(f"Max response time: {max(times):.4f} seconds")
    print(f"Min response time: {min(times):.4f} seconds")

if __name__ == "__main__":
    run_load_test()