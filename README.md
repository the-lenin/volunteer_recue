## Локальный запуск:
##### 1. Клонируем проект:
   В консоли (Bash Linux) заходим в нужную нам дирректорию и вводим:
   ```git clone git@github.com:DREU007/volunteer_recue.git```

##### 2. Переходим в дирректорию `/volunteer_recue` либо открываем проект в своей IDE.
   Устанавливаем зависимости и активируем виртуально окружение:
   ```
   poetry install
   poetry shell 
   ```
   
   В случае, если poetry не установлен, тогда переходим по ссылке 
   https://python-poetry.org/docs/#installing-with-pipx
   и устанавливаем согласно инструкции
   
##### 3. Установите библиотеку для обработки и анализа геопространственных данных 
```
   sudo apt update
   sudo apt install gdal-bin libgdal-dev
```
##### 4. Скопируйте файл `.env.example` в туже директорию, переименовав его в `.env`

##### 5. Создайте базу данных PostgreSQL:
```
   sudo apt install postgresql  - установка  PostgreSQL
   sudo apt-get install postgis  - установка расширения postgis
```   
   Создайте базу данных при помощи PGAdmin либо командной строк:
   https://www.postgresql.org/docs/   ссылка на официальную документацию
   Внесите данные о вашей базе даных в файл .env
   ```
   DATABASE_URL=postgis://[user[:password]@][hostname][:port][/dbname][?param1=value1&...]
   DATABASE_URL_EXT=postgres://[user[:password]@][hostname][:port][/dbname][?param1=value1&...]
   ```
   Например: `DATABASE_URL=postgis://andrey:bykmce76ce@localhost:5432/volounteers_test`
   
##### 6. Установите расширение PostGIS для вашей БД и сделайте связь проекта с вашей БД:
```
   make pg-extension   - устанавливает расширение PostGIS
   make migrate        - связывает проект с БД
   ```
   В случае, если при выполнении команды make migrate будет отказано в доступе, то выполните команду 

   make pg-extention-sudo     далее
   make migrate
   
##### 7. Создайте своего телеграмм бота через бот @BotFather (https://t.me/BotFather)
   заполните соответствующие поля в файле .env с токеном HTTP API 
   TELEGRAM_LINK=
   TELEGRAM_TOKEN=  
   
##### 8. Зарегистрируйтесь и получите свой токен для API в яндекс картах.
   https://yandex.com/dev/jsapi-v2-1/doc/en/#get-api-key кликните по ссылке на  `Developer's Dashboard`
   далее следуйте инструкции.
   Заполните поле в файле  `.env`
```
   YMAP_TOKEN=
```
   Далее заполните оставшиеся необходимые вам поля в этом файле.
   
##### 9. Запустите сервер django командой `make dev` либо `make prod`
   Запустите телеграмм бота командой `make bot-start`