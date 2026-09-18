# Pyssion

## 프로젝트 계승 · Project continuity

이 프로젝트는 제가 이전 GitHub 계정 **[CaptCore](https://github.com/CaptCore)**에서 개발하던
**[CaptCore/Pyssion](https://github.com/CaptCore/Pyssion)**을 이어가는 레포입니다.
이전 계정에 접근할 수 없게 되어 현재 계정 **[PrizmCaptCore](https://github.com/PrizmCaptCore)**의
**[PrizmCaptCore/Pyssion](https://github.com/PrizmCaptCore/Pyssion)**에서 개발을 이어갑니다.
기존 코드와 커밋 이력, MIT 라이선스 및 원저작자 표기를 유지합니다.

I originally developed Pyssion under my previous GitHub account, `CaptCore`.
After losing access to that account, I am continuing the project here under `PrizmCaptCore`,
preserving the existing code, commit history, original authorship, and MIT license.

---

`Pyssion.run()`

1. **Pack your code!**
2. **Shoot your code into kubernetes server & run your code! **

## main function

- **Easy Run**: only one method, `Pyssion.run()`
- **Automatic Container run**: Isolate each work
- **Run Server**: If you want to run your code, you can run Kubernetes Server or Your local! *If you want to run local, please install test_env.

## install

```bash
#git pull address
pip install -e .
```

## how to use

### .pyssionignore :
```
pyssion/
test/
pyssion.egg-info/
.git/
.gitignore
*.md
.pyssionignore
*.yaml
setup.py
```

### .pyssionenv :
```
# --- MinIO setting ---
MINIO_ENDPOINT=minio address
MINIO_ACCESS=minio id
MINIO_SECRET=minio password
MINIO_BUCKET=minio bucket

# --- Kubernetes setting ---
K8S_CONFIG=local.yaml
K8S_NAMESPACE=default  # if you didn't set this, we will use default set.

# --- entrypoint setting ---
ENTRYPOINT_FILE= your_entrypoint.py
REQ_FILE=req.txt

# --- Resource setting ---
GPU=1 #we can use only NVIDIA, We will soon update. Sorry !

# --- venv setting ---
USE_VENV_CACHE=0

# --- pyssion Cache drop setting ---
DELETE_PVC_AFTER_JOB=1
```

### test_code.py :
```python
#test_code.py
import sys
sys.dont_write_bytecode = True
from pyssion.core import Pyssion

if __name__ == "__main__":
    p = Pyssion()
    p.run()

```

## requirement

- Python 3.11 or latest
- rancher / minio (or S3)


This project is licensed under the MIT License – see the [LICENSE](./LICENSE) file for details.
