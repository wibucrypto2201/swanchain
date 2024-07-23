import os
from selenium import webdriver as uc
from time import sleep
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchWindowException
from selenium.webdriver.common.keys import Keys
from selenium_authenticated_proxy import SeleniumAuthenticatedProxy
from fake_useragent import UserAgent
import random
import csv
import urllib.parse
import threading
import atexit
import psutil

window_width = 1200
window_height = 1000
webs = []

def load_lines(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()
    lines = [line.strip() for line in lines]
    return lines

def write_lines(file_path, lines):
    with open(file_path, "w") as file:
        for line in lines:
            file.write(line + "\n")

def remove_line(file_path, line_to_remove):
    lines = load_lines(file_path)
    lines.remove(line_to_remove)
    write_lines(file_path, lines)

def handle_error(file_path, line):
    with open(file_path, "a") as file:
        file.write(line + "\n")

def arrange_windows(drivers, items_per_row, window_width, window_height):
    if not drivers:
        print("No drivers to arrange.")
        return
    screen_width = drivers[0].execute_script("return window.screen.availWidth")
    screen_height = drivers[0].execute_script("return window.screen.availHeight")
    for i, driver in enumerate(drivers):
        try:
            x_position = (i % items_per_row) * window_width
            y_position = (i // items_per_row) * window_height
            driver.set_window_position(x_position, y_position)
            driver.set_window_size(window_width, window_height)
        except NoSuchWindowException:
            print(f"Window for driver {i} is no longer available. Skipping arrangement.")

def kill_chrome_drivers():
    for proc in psutil.process_iter():
        try:
            if proc.name() == "chromedriver" or "chrome" in proc.name().lower():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

atexit.register(kill_chrome_drivers)

def task(tokenx, proxy, link_ref, tokens_file, semaphore):
    global webs
    web = None
    try:
        ua = UserAgent()
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        options = ChromeOptions()
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument('--log-level=3')
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--force-device-scale-factor=0.4")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Exclude "enable-automation" switch
        options.add_argument('--disable-blink-features=AutomationControlled')  # Disable blink features
        
        username, password_host_port = proxy.split('@')[0], proxy.split('@')[1]
        username, password = username.split(':')
        host, port = password_host_port.split(':')

        proxy_url = f"http://{username}:{password}@{host}:{port}"
        proxy_helper = SeleniumAuthenticatedProxy(proxy_url=proxy_url)
        proxy_helper.enrich_chrome_options(options)
        web = uc.Chrome(chrome_options=options)
        webs.append(web)
        arrange_windows(webs, 4, window_width, window_height)
        current = web.current_window_handle

        web.switch_to.window(current)
        web.switch_to.window(web.window_handles[0])
        web.switch_to.window(web.window_handles[0])
        web.execute_script("window.open('');")
        web.switch_to.window(web.window_handles[-1])
        web.get("https://x.com/")
        wait(web, 5).until(EC.presence_of_element_located((By.XPATH, "//*[text()[contains(.,'Home')]]"))) # Ensure the domain is loaded
        web.add_cookie({'name': 'auth_token', 'value': tokenx, 'domain': 'x.com'})
        web.refresh()
        print("Log in X Complete")
        web.close()
        web.switch_to.window(web.window_handles[0])
        web.switch_to.window(web.window_handles[-1])
        web.get(link_ref)
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Daily Combo')]]"))) 
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[1]/section/main/div[2]/div[1]/div/div[2]",
                )
            )
        ).click()
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Authorize')]]"))) 
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[2]/div/form/fieldset/input[1]",
                )
            )
        ).click()
        wait(web, 60).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'TOTAL POINTS')]]"))) 


    except NoSuchWindowException:
        print("Caught NoSuchWindowException. Skipping operation.")
        handle_error("fail_token.txt", tokenx)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        handle_error("fail_token.txt", tokenx)

    else:
        print("referral DONE", link_ref)
        remove_line(tokens_file, tokenx)

    finally:
        if web:
            webs.remove(web)
            web.close()
            web.quit()
            web = None
            semaphore.release()

def main():
    proxy_file = "proxy.txt"
    linkref_file = "linkref.txt"
    tokens_file = "token.txt"
    
    proxies = load_lines(proxy_file)
    links = load_lines(linkref_file)
    tokens = load_lines(tokens_file)
    print('=========================================')
    print('=        Auto referral Swanchain        =')
    print('=         Welcome to WibuCrypto         =')
    print('=      https://t.me/wibuairdrop142      =')
    print('=========================================')
    max_concurrent_tasks = int(input("Enter threads you want to: "))
    semaphore = threading.Semaphore(max_concurrent_tasks)
    
    threads = []
    for tokenx in tokens:  # Change to iterate directly over tokens
        proxy = random.choice(proxies)
        link_ref = random.choice(links)
        semaphore.acquire()
        t = threading.Thread(target=task, args=(tokenx, proxy, link_ref, tokens_file, semaphore))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()


if __name__ == '__main__':
    main()
