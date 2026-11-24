// Minimal owner component used by the fixture.
#[starknet::component]
pub mod OwnableComponent {
    use starknet::{ContractAddress, get_caller_address};
    use starknet::storage::{StoragePointerReadAccess, StoragePointerWriteAccess};

    #[storage]
    pub struct Storage {
        pub owner: ContractAddress,
    }

    #[generate_trait]
    pub impl InternalImpl<
        TContractState, +HasComponent<TContractState>,
    > of InternalTrait<TContractState> {
        fn initializer(ref self: ComponentState<TContractState>, owner: ContractAddress) {
            self.owner.write(owner);
        }

        fn assert_only_owner(self: @ComponentState<TContractState>) {
            assert(get_caller_address() == self.owner.read(), 'Caller is not the owner');
        }
    }
}
