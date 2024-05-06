# cdk
cdkを使用してAWS上にWebAPIを構築するテンプレート

## インストール

1. node.jsをインストール

- 下記からダウンロードしインストールする
  - [ダウンロード](https://nodejs.org/en/download/)

2. cdkをglobalインストールする

```
npm install -g aws-cdk
```

3. pythob仮想環境を作成し依存関係をインストールする

まず仮想環境（venv）を作成し仮想環境を有効化する

- windowsの場合
```
cd cdk
py -m venv .venv
.\.venv\Scripts\activate
```

- linuxの場合
```
cd cdk
python -m venv .venv
source .venv/bin/activate
```

仮想環境内にpipでインストール

```
pip install -r .\requirements.txt
```

## 使い方


1. AWSにログインした状態にする

- シングルサインオンを用いている場合
```
aws sso login
```

2. 仮想環境を有効化する

- windowsの場合
```
cd cdk
.\.venv\Scripts\activate
```

- linuxの場合
```
cd cdk
source .venv/bin/activate
```

3. （過去にこのAWSアカウントでcdkを使用していない場合のみ）

過去にこのAWSアカウントでcdkを使用していない場合、一度下記を実行すること

```
cdk bootstrap
```

4. deployする

```
cd cdk
cdk deploy --context api_spec=<path_to_api_spec_json>
```

例：sampleをデプロイする場合
```
cd cdk
cdk deploy --context api_spec=..\api_spec\sample\api_spec.json --context schema=..\api_spec\schema.json
```
