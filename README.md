# mitlesen-backend

## Run

```shell
uvicorn main:app --reload
```
```shell
sudo cp xrhub.service /etc/systemd/system/
sudo systemctl start xrhub
sudo systemctl enable 
sudo systemctl status xrhub

sudo apt update
sudo apt install nginx

sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

sudo ./venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 2 main:app --bind 0.0.0.0:80
```

## estimates

- gpt-4: $ 0.004 per summary
- gpt-4-mini: 0.002