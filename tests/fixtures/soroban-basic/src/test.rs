#![cfg(test)]
use super::*;
use soroban_sdk::{testutils::Address as _, Env};

#[test]
fn deposit_and_withdraw() {
    let env = Env::default();
    env.mock_all_auths();
    let admin = Address::generate(&env);
    let sac = env.register_stellar_asset_contract_v2(admin.clone());
    let vault = env.register(Vault, (admin.clone(), sac.address()));
    let client = VaultClient::new(&env, &vault);
    let user = Address::generate(&env);
    token::StellarAssetClient::new(&env, &sac.address()).mint(&user, &100);
    client.deposit(&user, &60);
    assert_eq!(client.balance(&user), 60);
    client.withdraw(&user, &user, &10);
    assert_eq!(client.balance(&user), 50);
}
