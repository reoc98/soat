import boto3

cognito = boto3.client('cognito-idp')

PROJECT_NAME = "soat"
NAME = "Fabian Admin"
USER_EMAIL = "test@rappi.com"
PASSWORD = "tempralPass123"
GROUPS = ["admin", "sponsor"]
SPONSOR = "rappi"

def create_user_pool(name):
    response = cognito.create_user_pool(
        PoolName=name,
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 10,
                # 'RequireUppercase': True,
                # 'RequireLowercase': True,
                # 'RequireNumbers': True,
                # 'RequireSymbols': True
            }
        },
        AutoVerifiedAttributes=['email'],
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Mutable': True,
                'Required': True
            },
            {
                'Name': 'sponsor',
                'AttributeDataType': 'String',
                'Mutable': True,
                'Required': False
            },
            {
                'Name': 'role',
                'AttributeDataType': 'String',
                'Mutable': True,
                'Required': False
            },
            {
                'Name': 'user_id',
                'AttributeDataType': 'String',
                'Mutable': True,
                'Required': False
            },
        ],
        UsernameAttributes=['email'],
        AdminCreateUserConfig={
            'AllowAdminCreateUserOnly': True
        }
    )
    user_pool_id = response['UserPool']['Id']
    print(f"✅ User Pool creado: {user_pool_id}")
    return user_pool_id

def create_user_pool_client(user_pool_id, name):
    response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f"{name}-app",
        GenerateSecret=False,
        ExplicitAuthFlows=[
            'ALLOW_USER_PASSWORD_AUTH',
            'ALLOW_REFRESH_TOKEN_AUTH',
            # 'ALLOW_USER_SRP_AUTH',
            # 'ALLOW_ADMIN_USER_PASSWORD_AUTH'
        ],
    )
    client_id = response['UserPoolClient']['ClientId']
    print(f"✅ App Client creado: {client_id}")
    return client_id

def create_group(user_pool_id, group_name, description=None, role_arn=None):
    cognito.create_group(
        GroupName=group_name,
        UserPoolId=user_pool_id,
        Description=description or f"Grupo {group_name}",
        # RoleArn=role_arn  # Opcional
    )
    print(f"✅ Grupo creado: {group_name}")

def create_user(user_pool_id):
    response = cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=USER_EMAIL,
        UserAttributes=[
            {'Name': 'email', 'Value': USER_EMAIL},
            {'Name': 'name', 'Value': NAME},
            {'Name': 'email_verified', 'Value': 'true'},
            {'Name': 'custom:sponsor', 'Value': SPONSOR},
            {'Name': 'custom:role', 'Value': "admin"},
            {'Name': 'custom:user_id', 'Value': "1"},
        ],
        MessageAction='SUPPRESS',  # Evita enviar email real
    )
    
    cognito.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=USER_EMAIL,
        Password=PASSWORD,
        Permanent=True
    )
    
    for group in GROUPS:
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=USER_EMAIL,
            GroupName=group
        )
    print(f"✅ Usuario creado: {USER_EMAIL}")
    return response

def add_user_to_group(user_pool_id, username, group_name):
    cognito.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username=username,
        GroupName=group_name
    )
    print(f"✅ Usuario '{username}' añadido al grupo '{group_name}'")


if __name__ == "__main__":
    # 1. Crear User Pool
    # user_pool_id = create_user_pool(PROJECT_NAME)

    # # 2. Crear App Client
    # create_user_pool_client(user_pool_id, PROJECT_NAME)

    # # 3. Crear grupos
    # for group in GROUPS:
    #     create_group(user_pool_id, group)

    # 4. Crear usuario
    # create_user(user_pool_id)

    # 5. Asignar a grupo
    # add_user_to_group(user_pool_id, USER_EMAIL, "sponsor")
    
    pass