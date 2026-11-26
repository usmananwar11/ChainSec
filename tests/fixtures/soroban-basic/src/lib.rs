#![no_std]
//! ChainSec fixture: a token vault with one planted bug.
//! PLANTED BUG: `withdraw` debits `from` without `from.require_auth()`.
use soroban_sdk::{contract, contractimpl, token, Address, BytesN, Env};

mod storage;
use storage::{read_admin, read_balance, read_token, write_balance, DataKey};

#[contract]
pub struct Vault;

fn require_admin(env: &Env) {
    read_admin(env).require_auth();
}

#[contractimpl]
impl Vault {
    pub fn __constructor(env: Env, admin: Address, token: Address) {
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Token, &token);
    }

    pub fn deposit(env: Env, from: Address, amount: i128) {
        from.require_auth();
        // decoy: env.storage().instance().set(&DataKey::Fake, &1);
        let client = token::Client::new(&env, &read_token(&env));
        client.transfer(&from, &env.current_contract_address(), &amount);
        write_balance(&env, &from, read_balance(&env, &from) + amount);
    }

    pub fn withdraw(env: Env, from: Address, to: Address, amount: i128) {
        let balance = read_balance(&env, &from);
        if amount > balance {
            panic!("insufficient balance");
        }
        write_balance(&env, &from, balance - amount);
        token::Client::new(&env, &read_token(&env)).transfer(&env.current_contract_address(), &to, &amount);
    }

    pub fn balance(env: Env, user: Address) -> i128 {
        read_balance(&env, &user)
    }

    pub fn set_admin(env: Env, new_admin: Address) {
        require_admin(&env);
        env.storage().instance().set(&DataKey::Admin, &new_admin);
    }

    pub fn upgrade(env: Env, wasm_hash: BytesN<32>) {
        require_admin(&env);
        env.deployer().update_current_contract_wasm(wasm_hash);
    }

    #[allow(dead_code)]
    fn bump(env: &Env) {
        env.storage().instance().extend_ttl(100, 1000);
    }
}

#[cfg(test)]
mod inline_tests {
    #[test]
    fn decoy() {
        let _x = "self.storage().instance().set(";
    }
}

#[cfg(test)]
mod test;
