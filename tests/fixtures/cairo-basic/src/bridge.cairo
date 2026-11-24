// Token bridge fixture. Planted bug: `deposit_from_l1` never checks `from_address`
// against the trusted L1 bridge, so any L1 contract can credit arbitrary balances.
#[starknet::interface]
pub trait IBridge<TContractState> {
    fn balance_of(self: @TContractState, user: starknet::ContractAddress) -> u256;
    fn withdraw_to_l1(ref self: TContractState, l1_recipient: felt252, amount: u256);
    fn set_l1_bridge(ref self: TContractState, l1_bridge: felt252);
}

#[starknet::contract]
pub mod Bridge {
    use starknet::{ContractAddress, get_caller_address, syscalls::send_message_to_l1_syscall};
    use starknet::storage::{
        Map, StoragePathEntry, StoragePointerReadAccess, StoragePointerWriteAccess,
    };
    use crate::components::ownable::OwnableComponent;

    component!(path: OwnableComponent, storage: ownable, event: OwnableEvent);
    impl OwnableInternalImpl = OwnableComponent::InternalImpl<ContractState>;

    #[storage]
    struct Storage {
        #[substorage(v0)]
        ownable: OwnableComponent::Storage,
        l1_bridge: felt252,
        balances: Map<ContractAddress, u256>,
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        #[flat]
        OwnableEvent: OwnableComponent::Event,
    }

    #[constructor]
    fn constructor(ref self: ContractState, owner: ContractAddress, l1_bridge: felt252) {
        self.ownable.initializer(owner);
        self.l1_bridge.write(l1_bridge);
    }

    #[l1_handler]
    fn deposit_from_l1(
        ref self: ContractState, from_address: felt252, user: ContractAddress, amount: u256,
    ) {
        let current = self.balances.entry(user).read();
        self.balances.entry(user).write(current + amount);
    }

    #[abi(embed_v0)]
    impl BridgeImpl of super::IBridge<ContractState> {
        fn balance_of(self: @ContractState, user: ContractAddress) -> u256 {
            self.balances.entry(user).read()
        }

        fn withdraw_to_l1(ref self: ContractState, l1_recipient: felt252, amount: u256) {
            let caller = get_caller_address();
            let current = self.balances.entry(caller).read();
            assert(current >= amount, 'Insufficient balance');
            self.balances.entry(caller).write(current - amount);
            let payload = array![l1_recipient, amount.low.into(), amount.high.into()];
            send_message_to_l1_syscall(self.l1_bridge.read(), payload.span()).unwrap();
        }

        fn set_l1_bridge(ref self: ContractState, l1_bridge: felt252) {
            self.ownable.assert_only_owner();
            self.l1_bridge.write(l1_bridge);
        }
    }
}
