# cdk
cdkを使用してAWS上にWebAPIを構築します

下記のリソースをAWS上に構築します
- lambda(sqs含む)
- batch (ecr含む)
- apigw
- s3
- sns

下記のリソースは構築しないので必要に応じて別途用意してください
- lambda layer
  - lambdaからlambda layerを参照する場合に必要
- vpc
  - batchを作成する場合に必要

リソースはapi_spec（API定義ファイル）の指定に従って作成されます。
api_specの記述仕様は[スキーマ定義](../api_spec/schema.json)を参照してください。

## 作成されるリソースの名前

作成されるリソースの名前は下記変数で決まります

|変数|指定場所|ハイフンの使用|アンダースコアの使用|
|--|--|--|--|
|bucket_name|`api_spec["s3"]`のkey名で指定|〇|×|
|api_name|`api_spec["name"]`の値で指定|〇|×|
|branch_name|`api_spec["stage"]`の各エントリの"branch"の値で指定|×|×|
|lambda_func_name|`api_spec["lambda_func_name"]`のkey名で指定|×|〇|
|batch_func_name|`api_spec["batch_func"]`のkey名で指定|×|〇|

作成されるリソースの名前は下記の通り命名されます

|リソース|名前|値|
|--|--|--|
|S3|バケット名|"{bucket_name}"|
|ApiGateway|GW名|"{api_name}"|
|Lambda|関数名|"{api_name}-{branch_name}-{lambda_func_name}"|
|SQS|トピック名|"{api_name}-{branch_name}-{lambda_func_name}_waiting"|
|SQS|トピック名|"{api_name}-{branch_name}-{lambda_func_name}_dead"|
|ECR|レジストリ名|"{api_name}-{batch_func_name}"|
|Batch|dockerイメージのtag名|"{account}.dkr.ecr.{region}.amazonaws.com/{api_name}-{batch_func_name}:{branch_name}"|

## リソースの詳細

lambda及びbatchには下記の環境変数が設定されます。

- Branch
  - branch_nameが設定されます
- API
  - api_nameが設定されます
- Bucket
  - `api_spec["stage"]`中でステージごとの`"bucket"`で定義した値が設定されます
  - API全体に渡って共通のs3に各lambdaやbatch中からアクセスする場合に、
    アクセス先のバケット名を指定しておくのに使用します
  - s3のバケットは別途自分で作成したものを参照することもできますし、
    このcdk中で`api_spec["s3"]`を指定して作成することも可能です
- NOTIFICATION_WEBHOOK_URL
  - `api_spec["stage"]`中でステージごとの`"notification_url"`で定義した値が設定されます
- NextSQS　※lambda専用
  - `api_spec["lambda_func"]`中でfuncごとに定義した値が設定されます
  - このlambdaの処理が終わった後に実行して欲しいSQSのキュー名を指定するのに使用します


### 作成されるAWS lambdaとSQS

- `api_spec["lambda_func"]`及び`api_spec["ref"]["lambda_layer"]`に従って、AWS lambdaを作成します。
- `"queue"`の指定をした場合は、SQSも合わせて作成します
- lambdaを実行する前に別途上記lambdaにコードをアップロードしてください
- (補足) lambdaレイヤーの指定
  - `api_spec["ref"]["lambda_layer"]`中で使用したいレイヤーのarnもしくはレイヤーの名前（バージョンを含まない）を指定します。
  - レイヤーの名前で指定した場合、その名前の（cdk実行時点で）最新のversionのレイヤーが自動的に選ばれます
  - 例：
  ```
  "lambda_layer": {
      "mylayer_1": "arn:aws:lambda:{$region}:{$account}:layer:mylayer:1",
      "mylayer_latest": "mylayer"
  }
  ```

### 作成されるAWS batchとECR

- `api_spec["batch_func"]`及び`api_spec["ref"]["vpc"]`に従って、AWS batchとECRを作成します
- このcdkではVPCを作成しません。cdk実行前に事前に別途VPCを作成しておく必要があります
- batchを実行する前に別途上記ECRレジストリに上記tag名でイメージをpushしておいてください

### 作成されるAPI gateway
- `api_spec["apigw"]`に従って、lambdaを実行するためのAPI gatewayを作成します
- アクセス先のlambdaは、`api_spec["lambda_func"]`中で指定してください。

### 作成されるS3
- `api_spec["s3"]`に従ってlambdaやbatchからアクセスするS3を作成します

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
cdk deploy --context api_spec=<api_specへのパス> --context schema=<api_specのスキーマへのパス>
```

例：sampleをデプロイする場合
```
cd cdk
cdk deploy --context api_spec=api_spec\sample\api_spec.json
```
