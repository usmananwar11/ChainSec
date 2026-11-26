use soroban_sdk::{contracttype, Address, Env};

#[derive(Clone)]
#[contracttype]
pub enum DataKey {
    Admin,
    Token,
    Balance(Address),
}

pub fn read_admin(env: &Env) -> Address {
    env.storage().instance().get(&DataKey::Admin).unwrap()
}

pub fn read_token(env: &Env) -> Address {
    env.storage().instance().get(&DataKey::Token).unwrap()
}

pub fn read_balance(env: &Env, id: &Address) -> i128 {
    env.storage().persistent().get(&DataKey::Balance(id.clone())).unwrap_or(0)
}

pub fn write_balance(env: &Env, id: &Address, amount: i128) {
    env.storage().persistent().set(&DataKey::Balance(id.clone()), &amount);
}
