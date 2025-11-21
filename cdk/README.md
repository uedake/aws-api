# cdkの利用
cdkを使用してAWS上にWebAPI及びWebAPIを使用するWebAppのリソースを構築します。
リソースはspec定義（jsonで書かれた定義ファイル）の指定に従って作成されます。
記述仕様の詳細は[スキーマ定義](spec/schema.json)を参照してください。

- 下記のリソースをAWS上に構築します

|リソース|作成単位|作成有無|設定場所|
|--|--|--|--|
|S3|共通|任意|`spec["s3"]`で指定|
|Amplify|共通|任意|`spec["amplify"]`で指定|
|API Gateway|共通|任意|`spec["apigw"]`を指定|
|SNS|共通|任意|`spec["sns"]`を指定|
|Lambda(SNS用)|共通|任意|`spec["sns"][topic_key]["lambda_func"]`を指定|
|Lambda(通常)|ステージ毎|必ず|`spec["lambda_func"]`で指定|
|SQS|ステージ毎|任意|`spec["lambda_func"][lambda_key]["queue"]`を指定|
|Batch|ステージ毎|任意|`spec["batch_func"]`を指定|
|ECR|共通|任意|`spec["batch_func"]`を指定|

- 下記のリソースは構築しないので必要に応じて別途事前に用意してください
  - lambda layer
    - Lambdaからlambda layerを参照する場合に必要
  - vpc
    - Batchを作成する場合に必要
  - domain(Route53)
    - Amplifyを作成する場合に必要
  - cognito
    - Lambdaのアクセスに認証をかけたい場合

## 作成されるリソースの名前

作成されるリソースの名前はspec定義中の値で決まります。名前に影響を与える値を本READMEの説明中では変数と考え、下記表の通り定義します。

|変数|指定場所|ハイフンの使用|アンダースコアの使用|大文字の使用|
|--|--|--|--|--|
|api_name|`spec["name"]`の値で指定|〇|×|×|
|branch_name|`spec["branch"]`のkey名で指定|〇|×|〇|
|bucket_name|`spec["s3"]`のkey名で指定|〇|×|×|
|app_name|`spec["amplify"]`のkey名で指定|〇|×|〇|
|topic_key|`spec["sns"]`のkey名で指定|〇|〇|〇|
|lambda_key|`spec["lambda_func"]`のkey名で指定|×|〇|〇|
|sns_lambda_key|`spec["sns"][topic_key]["lambda_func"]`のkey名で指定|×|〇|〇|
|batch_key|`spec["batch_func"]`のkey名で指定|×|〇|〇|

作成されるリソースの名前は下記の通り命名されます

|リソース|名前|値|
|--|--|--|
|S3|バケット名|"{bucket_name}"|
|Amplify|アプリ名|"{app_name}"|
|API Gateway|GW名|"{api_name}"|
|SNS|トピック名|"{api_name}-{topic_key}"|
|Lambda|関数名|"{api_name}-{branch_name}-{lambda_key}"|
|Lambda|関数名|"{api_name}-{sns_lambda_key}"|
|SQS|キュー名|"{api_name}-{branch_name}-{lambda_key}_waiting"|
|SQS|キュー名|"{api_name}-{branch_name}-{lambda_key}_dead"|
|ECR|レジストリ名|"{api_name}-{batch_key}"|
|Batch|Batch名|"{api_name}-{branch_name}-{batch_key}"|
|Batch|dockerイメージのtag名|"{account}.dkr.ecr.{region}.amazonaws.com/{api_name}-{batch_key}:{branch_name}"|

## API gatewayのアクセスに認証をかけたい場合

- 事前にcognitoのIDプールとアプリケーションクライアントを作成し、そのIDを`spec["ref"]["cognito"]`に設定してください。
- API gatewayではルート単位で認証を設定できます。
  - `spec["apigw"]["lambda"][lambda_key]["cognito_auth"]`に`spec["ref"]["cognito"]`のキー名を指定してください。
  - WebアプリからAPI gatewayの認証付きルートにアクセスするには、`spec["amplify"][app_name]["cognito_auth"]`に同じ値を指定してください。

## 環境変数

Lambda/Batch/Amplifyには下記の環境変数が設定されます。
Amplifyの環境変数は.envファイルに設定されるので、dotenvパッケージを使用して読み込んでください。

- Branch
  - branch_nameが設定されます
- API
  - api_nameが設定されます
- Bucket
  - `spec["branch"][branch_name]["bucket"]`で定義した値が設定されます
  - API全体に渡って共通のs3にアクセスする場合に、アクセス先のバケット名を指定しておくのに使用します
  - s3のバケットは別途自分で作成したものを参照するか、このcdkで作成したものを指定可能
- NOTIFICATION_WEBHOOK_URL
  - `spec["branch"][branch_name]["notification_url"]`で定義した値が設定されます
- NextSQS　※lambda専用
  - `spec["lambda_func"][lambda_key]["queue_next"]`で参照したLambdaを実行する為のキュー名が設定されます
  - あるLambdaの処理が終わった後に実行したいLambdaを指定するのに使用します。

## リソースの詳細

### AWS lambdaとSQS

- `spec["ref"]["lambda_layer"]`
- cdkでのリソース作成時に、初期コードを合わせてアップロードできます。
- 初期コードをアップロードしない場合や、その後更新したい時は、cdkでリソース作成後に別途コードをアップロードしてください
- `spec["lambda_func"][lambda_key]["queue"]`の指定をした場合、このLambdaを実行する為のSQSも合わせて作成します
- lambdaレイヤーの指定方法
  - `spec["ref"]["lambda_layer"]`中で使用したいレイヤーのarnもしくはレイヤーの名前（バージョンを含まない）を指定します。
  - レイヤーの名前で指定した場合、その名前の（cdk実行時点で）最新のversionのレイヤーが自動的に選ばれます
  - 例：
  ```
  "lambda_layer": {
      "mylayer_1": "arn:aws:lambda:{$region}:{$account}:layer:mylayer:1",
      "mylayer_latest": "mylayer"
  }
  ```

### AWS batchとECR
- このcdkではVPCを作成しません。cdk実行前に事前に別途VPCを作成し、`spec["ref"]["vpc"]`に参照を記述する必要があります。
- cdkでリソース作成後、batchを実行する前に別途上記ECRレジストリにこのcdkで作成されるtag名を指定してイメージをpushしてください

### API gateway
- アクセス先のLambda定義は、`spec["lambda_func"]`中で指定します
- `spec["apigw"]["lambda_integration"]`のkeyで上記Lambda定義と同じキー（lambda_key）を指定してルートを設定します。

### S3
- Lambda/Batch/Amplifyからs3を使用したい場合下記の方法があります
- このcdkで作成されたS3を使用する場合
  - `spec["branch"][branch_name]["bucket"]`に`spec["s3"]`で指定したキー（bucket_name）を指定します
- このcdk外で作成されたS3を使用する場合
  - `spec["branch"][branch_name]["bucket"]`にバケット名を指定します。
- 上記で指定したバケット名は、Lambda/Batch/Amplifyの環境変数に設定されます

### Amplify
- Amplifyのソースコードはgithubに置かれることを前提とし、CI/CDを構築します
- cdk実行前に下記操作をしてください
　- githubに「Amplify GitHub アプリケーション」をインストールし、対象リポジトリへのアクセスを許可
    - amplify consoleから行うのが簡便。適当なamplifyアプリを作成しgithubとつなげることで設定が作成可能
  - githubでpatを作成し、cdkを実行するマシンの環境変数GITHUB_PATに設定
  - レポジトリのユーザーURL（`https://github.com/hogehoge`の形式）を`spec["repository_root"]`に設定
  - `spec["amplify"]`のキー（app_name）と同じ名前でレポジトリを作成
- cdk実行後に下記のいずれかの方法でデプロイをしてください
  - 方法１）レポジトリにコードをpushする
  - 方法２）Amplifyのコンソール上でデプロイを指示する

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


1. スクリプトがAWSにアクセスできる状態にする

- secretアクセスキーを用いる場合
```
aws configure
```

- シングルサインオンを用いる場合
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
cdk deploy --context spec=<specへのパス>
```

例：sample-apiをデプロイする場合
```
cd cdk
cdk deploy --context spec=spec\sample-api\api_spec.json
```
