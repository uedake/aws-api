# cdk
cdkを使用してAWS上にWebAPIを構築します

下記のリソースをAWS上に構築します
- lambda
- batch (ecr含む)
- apigw
- sqs
- s3

下記のリソースは構築しないので必要に応じて別途用意してください
- lambda layer
  - lambdaからlambda layerを参照する場合に必要
- vpc
  - batchを作成する場合に必要

リソースはapi_specの指定に従って作成されます

## 作成されるリソースの詳細

作成されるリソースの名前は下記の部分名称を使って命名されます
- api_name
  - api_spec["name"]で指定します
- branch_name
  - api_spec["stage"]の中で指定します（複数指定可能）

### 作成されるAWS lambda
api_spec["lambda_func"]及び及びapi_spec["ref"]["lambda_layer"]に従って、AWS lambdaを作成します
- 下記名前のlambdaを作成します
  - "{api_name}-{branch_name}-{lambda_func_name}"
{lambda_func_name}はapi_spec["lambda_func"]のkey名が使用されます

lambdaを実行する前に別途上記lambdaにコードをアップロードしておいてください

(補足) lambdaに設定される環境変数
- Bucket
  - api_spec["stage"]中でステージごとに定義した値が設定されます
  - API全体に渡って共通のs3に各lambda中からアクセスする場合に、
    アクセス先のバケット名を指定しておくのに使用します
  - s3のバケットは別途自分で作成したものを参照することもできますし、
    このcdk中でapi_spec["s3"]を指定して作成することも可能です
- Branch
  - branch_nameが設定されます
- API
  - api_nameが設定されます
- NextSQS
  - api_spec["lambda_func"]中でfuncごとに定義した値が設定されます
  - このlambdaの処理が終わった後に実行して欲しいSQSのキュー名を指定するのに使用します

(補足) lambdaレイヤーの指定
api_spec["ref"]["lambda_layer"]中で使用したいレイヤーのarnもしくはレイヤーの名前（バージョンを含まない）を指定します。
レイヤーの名前で指定した場合、その名前の（cdk実行時点で）最新のversionのレイヤーが自動的に選ばれます

例：
```
"lambda_layer": {
    "mylayer_1": "arn:aws:lambda:{$region}:{$account}:layer:mylayer:1",
    "mylayer_latest": "mylayer"
}
```

### 作成されるAWS batchとECR
api_spec["batch_func"]及びapi_spec["ref"]["vpc"]に従って、AWS batchとECRを作成します
- 下記名前のECRレジストリを作成します
  - "{api_name}-{batch_func_name}"
- 下記名前のtagを持つdockerイメージを実行するbatchを作成します
  - "{account}.dkr.ecr.{region}.amazonaws.com/{api_name}-{batch_func_name}:{branch_name}"
{batch_func_name}はapi_spec["batch_func"]のkey名が使用されます

このcdkではVPCを作成しません。cdk実行前に事前に別途VPCを作成しておく必要があります
batchを実行する前に別途上記ECRレジストリに上記tag名でイメージをpushしておいてください

### 作成されるAPI gateway
api_spec["apigw"]に従って、lambdaを実行するためのAPI gatewayを作成します
- 下記名前のAPI gatewayを作成します
  - "{api_name}"

アクセス先のlambdaは、api_spec["lambda_func"]中で指定してください。

### 作成されるSQS
api_spec["sqs_for_lambda"]に従ってlambdaを実行するためのSQSを作成します
- 下記名前のSQSを作成します
  - "{api_name}-{branch_name}-{lambda_func_name}_waiting"
  - "{api_name}-{branch_name}-{lambda_func_name}_dead"
{lambda_func_name}はapi_spec["sqs_for_lambda"]のkey名が使用されます

アクセス先のlambdaは、api_spec["lambda_func"]中で指定してください。

### 作成されるS3
api_spec["s3"]に従ってlambdaを実行するためのS3を作成します
- 下記名前のS3を作成します
  - "{bucket_name}"
{bucket_name}はapi_spec["s3"]のkey名が使用されます


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
cdk deploy --context api_spec=..\api_spec\sample\api_spec.json --context schema=..\api_spec\schema.json
```

例：sampleをデプロイする場合
```
cd cdk
cdk deploy --context api_spec=..\api_spec\sample\api_spec.json --context schema=..\api_spec\schema.json
```
